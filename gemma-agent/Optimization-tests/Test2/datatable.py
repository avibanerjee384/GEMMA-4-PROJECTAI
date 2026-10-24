import pandas as pd
from pathlib import Path

df = summary_df if 'summary_df' in globals() else pd.read_csv('/kaggle/working/run_summary.csv')
df = df.reset_index(drop=True)


def to_markdown_table(frame, index_label='#'):
    esc = lambda v: str(v).replace('|', '\\|')  # a literal | would break a GitHub table
    headers = [index_label] + [esc(c) for c in frame.columns]
    lines = ['| ' + ' | '.join(headers) + ' |',
             '|' + '|'.join('---' for _ in headers) + '|']
    for i, row in frame.iterrows():
        lines.append('| ' + ' | '.join([str(i)] + [esc(v) for v in row.tolist()]) + ' |')
    return '\n'.join(lines)


md_table = to_markdown_table(df)
print(md_table)
Path('/kaggle/working/run_summary_table.md').write_text(md_table + '\n')
