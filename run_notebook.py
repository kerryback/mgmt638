import nbformat
from nbconvert.preprocessors import ExecutePreprocessor

# Read notebook
with open('session11A_interpretability.ipynb', 'r', encoding='utf-8') as f:
    nb = nbformat.read(f, as_version=4)

# Execute
ep = ExecutePreprocessor(timeout=600, kernel_name='python3')

try:
    out = ep.preprocess(nb)
    print("Notebook executed successfully!")

    # Save executed notebook
    with open('session11A_interpretability_executed.ipynb', 'w', encoding='utf-8') as f:
        nbformat.write(nb, f)
    print("Saved executed notebook")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
