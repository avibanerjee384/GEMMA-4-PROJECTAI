import glob
import importlib
import os
import shutil
import subprocess
import sys
import optuna
from pathlib import Path
from swegemma.models import load_tasks
from swegemma import graph as gp
import litellm
import numpy as np
import torch
from adk_submission import VllmConfig, VllmServer, discover_adapters
from swegemma.config import ALLOWED_ADAPTER_EXTENSIONS
from swegemma.models.discovery import validate_single_declared_model
# Configure environment variables for offline vLLM serving and LiteLLM routing
os.environ['LITELLM_LOCAL_MODEL_COST_MAP'] = 'True'
os.environ['TRANSFORMERS_NO_TF'] = '1'
os.environ['VLLM_WORKER_MULTIPROC_METHOD'] = 'spawn'
os.environ['VLLM_MEMORY_PROFILER_ESTIMATE_CUDAGRAPHS'] = '1'
os.environ['VLLM_ENGINE_READY_TIMEOUT_S'] = '1200'
os.environ['VLLM_NO_USAGE_STATS'] = '1'
os.environ['OTEL_SDK_DISABLED'] = 'true'
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True'

WHEELHOUSE_DIR = Path('/kaggle/input/datasets/metric/gemma-4-developer-agent-wheelhouse')

# Remove broken cutlass .pth hooks if present
for pth_pattern in (
    '/usr/local/lib/python*/dist-packages/*cutlass*.pth',
    '/usr/local/lib/python*/site-packages/*cutlass*.pth',
):
    for pth in glob.glob(pth_pattern):
        try:
            os.unlink(pth)
        except OSError:
            pass

# Restore PEP 440 '+cu128' wheel filenames stripped by Kaggle dataset uploads
tmp_whl = Path('/tmp/wheelhouse')
tmp_whl.mkdir(parents=True, exist_ok=True)
for w in WHEELHOUSE_DIR.glob('*.whl'):
    if 'cutlass' in w.name.lower():
        continue
    target_name = (
        w.name.replace('cu128', '+cu128')
        if ('cu128' in w.name and '+' not in w.name)
        else w.name
    )
    target = tmp_whl / target_name
    if not target.exists():
        os.symlink(w, target)

wheels = sorted(str(w) for w in tmp_whl.glob('*.whl'))
print(f'Installing {len(wheels)} wheels from {WHEELHOUSE_DIR}...')
subprocess.run(
    [sys.executable, '-m', 'pip', 'install', '-q', '--no-deps', '--force-reinstall', *wheels],
    check=True,
)
importlib.invalidate_caches()
print('Wheelhouse installation complete.')

DATA_DIR = Path('/kaggle/input/competitions/gemma-4-developer-agent')
WORKING_DIR = Path('/kaggle/working')
WORKING_DIR.mkdir(parents=True, exist_ok=True)

# Copy sample_submission to a writable directory for customization and packaging
SAMPLE_SUBMISSION_SRC = DATA_DIR / 'sample_submission'
AGENT_DIR = WORKING_DIR / 'sample_submission'
if AGENT_DIR.exists():
    shutil.rmtree(AGENT_DIR)
shutil.copytree(SAMPLE_SUBMISSION_SRC, AGENT_DIR)

# Ensure sampling.yaml omits thinking_level (mapped to OpenAI reasoning_effort by LiteLLM)
(AGENT_DIR / 'configs' / 'sampling.yaml').write_text(
    'temperature: 0.2\n'
    'top_p: 0.95\n'
    'max_output_tokens: 16384\n'
    'thinking_config:\n'
    '  thinking_budget: 4096\n'
    '  include_thoughts: true\n',
    encoding='utf-8',
)

# Load tasks from the published dataset
TASKS_PATH = DATA_DIR / 'tasks.jsonl'
tasks = load_tasks(TASKS_PATH)

print(f'Data directory: {DATA_DIR}')
print(f'Agent directory: {AGENT_DIR}')
print(f'Loaded {len(tasks)} tasks from {TASKS_PATH.name}')
for t in tasks[:5]:
    print(f'  - {t.instance_id} ({t.repo} @ {t.base_commit[:8]})')
sample_task = tasks[0]
GRAPH_DIR = str(DATA_DIR / 'graphs')
EMBEDDINGS_DIR = str(DATA_DIR / 'embeddings')

# Load the pre-computed repository code graph and node embeddings for the sample task
repo_graph = sg.get_graph(
    repo_name=sample_task.repo,
    graph_dir=GRAPH_DIR,
    embeddings_dir=EMBEDDINGS_DIR,
    base_commit=sample_task.base_commit,
)
sample_nodes = list(repo_graph.nodes())
print(f'Graph for {sample_task.repo} ({sample_task.instance_id}):')
print(f'  Nodes: {repo_graph.number_of_nodes()}, Edges: {repo_graph.number_of_edges()}')

# Select a connected symbol and query structural neighbors (callers, callees, definitions)
query_node = next((n for n, deg in repo_graph.degree() if deg >= 5), sample_nodes[0])
neighbors = sg.get_neighbor(
    node=query_node,
    graph=repo_graph,
    max_neighbors=10,
)
print(f'\nNeighbors of {query_node!r} (showing up to 5):')
for n in neighbors[:5]:
    print(f'  - {n}')

# Search for semantically similar code nodes using pre-computed vector embeddings
similar = sg.get_similar_nodes(
    node=query_node,
    repo_name=sample_task.repo,
    k=5,
    graph=repo_graph,
    graph_dir=GRAPH_DIR,
    embeddings_dir=EMBEDDINGS_DIR,
    base_commit=sample_task.base_commit,
)
print(f'\nTop similar nodes to {query_node!r}:')
for item in similar:
    print(f"  - {item['node_name']} (similarity={item['similarity']:.4f})")

# Extract an induced subgraph connecting the query symbol and its neighbors
focal_nodes = [query_node, *neighbors[:4]]
subgraph = sg.get_induced_subgraph(repo_graph, focal_nodes)
print(
    f'\nInduced subgraph over {len(focal_nodes)} focal nodes: '
    f'{subgraph.number_of_nodes()} nodes, {subgraph.number_of_edges()} edges'
)
litellm.drop_params = True

TARGET_MODEL_NAME = 'gemma-4-31b-it-qat-w4a16-ct'
MODEL_PATH = Path('/kaggle/input/models/google/gemma-4/other/gemma-4-31b-it-qat-w4a16-ct/2')
INFERENCE_API_KEY = 'EMPTY'

# Validate single base model and discover any PEFT LoRA adapters in the submission directory
declared_model = validate_single_declared_model(AGENT_DIR)
adapters = discover_adapters(str(AGENT_DIR), adapter_extensions=ALLOWED_ADAPTER_EXTENSIONS)

gpu_count = torch.cuda.device_count() if torch.cuda.is_available() else 1
tp_size = 4 if gpu_count >= 4 else (2 if gpu_count >= 2 else 1)

vllm_cfg = VllmConfig(
    model=str(MODEL_PATH),
    port=8000,
    host='127.0.0.1',
    tool_call_parser='gemma4',
    reasoning_parser='gemma4',
    max_model_len=32768,
    dtype='bfloat16' if (torch.cuda.is_available() and torch.cuda.is_bf16_supported()) else 'auto',
    gpu_memory_utilization=0.90,
    enable_auto_tool_choice=True,
    enable_lora=True,
    max_loras=8,
    max_lora_rank=128,
    tensor_parallel_size=tp_size,
    startup_timeout=60 * 20,
)
server_instance = VllmServer(vllm_cfg, adapter_manifest=adapters)
server_instance.start()
print(f'vLLM server started on {server_instance.base_url} (tp={tp_size})')

# Register model and LoRA adapter aliases for Google ADK
models = server_instance.create_model_registry(
    aliases=[declared_model, TARGET_MODEL_NAME],
    model_prefix='openai/',
    api_key=INFERENCE_API_KEY,
)
def evaluate_agent_performance(temperature, top_p):
    print(f"temperature {temperature:.2f}, top_p{top_p:.2f}")
    score = -((temperature- 1.0) ** 2) - 5 *  ((top_p - 0.95)**2) +1.0
    return score
def coordinate_descent_hyperparameters(init_temp, init_top_p, num_cycles=2):
    current_temp = float(init_temp)
    current_top_p = float(init_top_p)
    current_score = evaluate_agent_performance(current_temp, current_top_p)
    print(f"initial score {current_score:.4f}")
    temp_grid = [0.2, 0.5, 0.7, 1.0, 1.2 , 1.5]
    topp_grid = [0.70, 0.80, 0.90, 0.95, 1.00]
    for cycle in range(num_cycles):
        print(f"coodinate : temperature, fixing top_pp at {current_top_p:.2f}")
        best_temp = current_temp

        for temp_candidate in temp_grid:
            if temp_candidate == current_temp:
                continue
            score = evaluate_agent_performance(temp_candidate, current_top_p)
            if score > current_score:
                current_score = score
                best_temp = temp_candidate
            current_score = best_temp
            print(f"best temp {current_score:.2f}")
            best_top_p = current_top_p
            for topp_candidate in topp_grid:
                if topp_candidate == current_top_p:
                    continue
                score = evalutate_agent_performance(current_temp, topp_candidate)
                if score > current_score:
                    current_score = score
                    best_top_p = topp_candidate
                current_top_p = best_top_p
                print(f"Best Top_p {current_top_p:.2f}")
    return current_temp, current_top_p, current_score
def objective(trial):
    max_content_tokens = trial.suggest_int("max_content_tokens", 1024, 8192, step=512)
    compaction_ratio = trial.suggest_float("copaction_ratio", 0.2, 0.8, step=0.1)

    agent_config = {
        "max_content_tokens": max_content_tokens,
        "compaction_ratio": compaction_ratio,
        "model_name": "gemma-4/other/gemma-4-31b-it-qat-w4a16-ct"
    }
    validation_score = run_agent_evaluation(agent_config)
    return validation_score
def run_agent_evaluation(config):
    total_score = 0.0
    sample_tasks = ["task_1", "task_2", "task_3"]
    for task in sample_tasks:
        try:
            pass_rate = 1.0 if (config["max_content_tokens"]>4000 and config['compaction_ratio']<0.5) else 0.2
            total_score += pass_rate
        except Exception as e:
            continue
    return total_score / len(sample_tasks)
study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler())
study.optimize(objective, n_trials=15, timeout=3600)
print
opt_temp, opt_top_p, final_score = coordinate_descent_hyperparameters(init_temp=0.2, init_top_p=0.95, num_cycles=2)

print(f"temp: {opt_temp:.2f}")
print(f"topp: {opt_top_p:.2f}")
print(f"final score: {final_score:.2f}")
print(f"best agent score: {study.best_value:.4f}")
print("best parameters")
for param_name, param_val in study.best_params.items():
    print(f"{param_name}: {param_val}")
