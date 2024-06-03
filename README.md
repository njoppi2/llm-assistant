# llm-assistant

To develop this project, I used pipenv, in order to isolate the livraries used in this project from the other projects in my computer. To create the python environment, i did:

```bash
pipenv install dependency1 dependency2 ... dependencyN
 ```

But, since the dependencies are store inside the Pipfile, you can just make sure you're in the root directory, and run:

```bash
pipenv install
```

To active the environment the currenct environment created from your shell, just run.

 ```bash
 pipenv shell 
 ```

However, if you don't want to load the environment into your current shell, you can directly use it with ```pipenv run``` to run python files, like so:

 ```bash
pipenv run uvicorn main:app --reload
pipenv run python main.py
 ```
 