from unstructured.partition.pdf import partition_pdf

from transformers import logging
logging.set_verbosity_error()

from datetime import datetime 
import os
def get_filenames_in_directory(directory_path):
    # List to store filenames
    filenames = []

    # Iterate over all entries in the directory
    for entry in os.listdir(directory_path):
        # Get the full path
        full_path = os.path.join(directory_path, entry)

        # Check if it's a file and add to the list
        if os.path.isfile(full_path) and entry[0] != '.':
            filenames.append(entry)

    return filenames

dirpath = './pdffiles'
filenames = get_filenames_in_directory(dirpath)

for filename in filenames:
    print(f'Processing {filename} at {datetime.now():%b %d %I:%M %p}')
    elements = partition_pdf(filename=f'{dirpath}/html_files/{filename}', infer_table_structure=True)
    tables = [el for el in elements if el.category == "Table"]
    filetoken = filename.split('.')[0].replace(' ', '')

    for n,t in enumerate(tables): 
        with open(f"./pdffiles/{filetoken}_table_{n}.html", "w") as file1:
            # Writing data to a file
            file1.write(t.metadata.text_as_html)

# print(tables[0].text)
# print(tables[0].metadata.text_as_html)

