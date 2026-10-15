# Labeling rubric

Fill the `label` column of label_sheet.csv with one word per record:

- **drop**: a reviewer would NOT want this record in a training set because of a
  defect this pipeline targets: malformed or empty content, boilerplate or spam,
  endless repetition, gibberish, text in a language outside the allowed set,
  personal data, leaked benchmark text, or a near-copy of another record.
  Navigation or date-only stubs with no running text count as drop.
- **keep**: none of those defects apply.
- **skip**: you cannot judge it (for example, you cannot read the language).

Do not label drop for reasons the pipeline does not target: factual mistakes,
mediocre but valid answers, or opinions you disagree with.

Judge each record on its own. The sheet is shuffled and does not show which
filter handled it. Do not edit the `id` column.
