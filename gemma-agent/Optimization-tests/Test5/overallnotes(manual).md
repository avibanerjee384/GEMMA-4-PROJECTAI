_(done 100% manually so will be simpler)_ 

## Notes
- 4 nonexistent patches, so that rule isn't being applied properly. To solve, we need to make an edit of not nothing by some threshold time
- Tool calls fine, maybe raise to 40 or smth
- Can lower submission token counts to give more budget to other parts (maybe halve tokens and increase thinking power)
- Many of these entries have a tendency to desire short patches, as there are pretty small issues. May want to lower token count if optimizing to this dataset, but we don't know what the other one will be like.
- VERY few syntax errors so that is good (at least as far as I can tell)
- Overall, patch quality is lacking, so will have to move into LORA adapting for that as soon as most other issues are cleared up.
- Have to figure out how to stop no submitted patches, because just saying "you need to submit a patch by the end" can submit an empty patch, or none at all.
