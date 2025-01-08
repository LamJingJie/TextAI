# TextAI
## End Goal
- Generate related texts and summaries/descriptions from images and context.
- If an image contains only text, return the text itself as a description and related texts about it.

## Introduction
- This tool is used to process images and generate related texts and summaries.

##
- Kept at low temperature (0.3) to ensure reprodability of img description. Too high it may start halucinating and generate gibberish

## Initialization
Navigate to the parent folder and run the following commands:


1. Install Virtual Env
```sh
python install pipenv
```

2. Activate Virtual Env
```sh
pipenv shell
```

3. Install relevant dependicies
```sh
pipenv install
```

4. Install playwright files
```sh
playwright install
```

5. Run program
```sh
python main.py
```
