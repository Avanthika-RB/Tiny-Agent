# Day 1 notes

Run:

```
python day1_embeddings.py
```

## What is a dimension?

It says we embedded 20 sentences with vector length (dimension) at 2048. Dimension is the vector length where every sentence became a list of 2048 numbers where each is a coordinate in 2048-dimensional space, 1 number doesnt have much meaning but shows the similarity between different points in that space.

## What does cosine similarity measure?

It measures how close the vectors point in a direction, measures similarity between the text by making arrows/angles between each point.

Then we rank by seeing which sentences score higher than others for the same question

## Why is the same text embedded two different ways?

There is query and passage, 2 different ways or modes used. This is because model uses query mode for questions and passage mode for stored text. This puts the questions near answers so that search can return the closest stored text to the questions vector.
