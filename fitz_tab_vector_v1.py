'''
https://pymupdf.readthedocs.io/en/latest/page.html#Page.find_tables
https://pypi.org/project/PyMuPDF/1.23.9/
PYDEVD_WARN_EVALUATION_TIMEOUT environment variable to a bigger value

https://www.docugami.com/pricing

(clip=None, vertical_strategy='lines', horizontal_strategy='lines', 
vertical_lines=None, horizontal_lines=None, 
snap_tolerance=3, snap_x_tolerance=None, snap_y_tolerance=None, 
join_tolerance=3, join_x_tolerance=None, join_y_tolerance=None, 
edge_min_length=3, 
min_words_vertical=3, min_words_horizontal=1, 
intersection_tolerance=3, intersection_x_tolerance=None, intersection_y_tolerance=None, 
text_tolerance=3, text_x_tolerance=3, text_y_tolerance=3)

row_rgb = {f'{n:02d}':(# page.get_pixmap(clip = row.cells[0]).colorspace.this.Fixed_RGB,
                        # page.get_pixmap(clip = row.cells[0]).color_topusage()[0],
                        
                        sum(1 for item in tbl.extract()[n] if len(item) > 0),
                        tbl.extract()[n][0])
            for n,row in enumerate (tbl.rows)}

# freq = [len(row.cells) for row in tbl.rows]
# counts = {item:freq.count(item) for item in freq}
# pp.pprint(counts)

# for n,row in enumerate (tbl.rows):
#    rgb = page.get_pixmap(clip = row.cells[0]).px.colorspace.this.Fixed_BGR

https://github.com/langchain-ai/langchain/blob/master/cookbook/Semi_Structured_RAG.ipynb?ref=blog.langchain.dev 
https://python.langchain.com/docs/modules/data_connection/retrievers/multi_vector
https://levelup.gitconnected.com/a-guide-to-processing-tables-in-rag-pipelines-with-llamaindex-and-unstructuredio-3500c8f917a7


https://pymupdf.readthedocs.io/en/latest/recipes-text.html#how-to-extract-text-in-natural-reading-order

https://pymupdf.readthedocs.io/en/latest/recipes-text.html#how-to-analyze-font-characteristics


'''        
import os
import ast
import re
from dotenv import load_dotenv
# fitz is the PDF parser with table recognize capabilities 
import fitz
from datetime import datetime 
from difflib import SequenceMatcher

# langchain connects components of a LLM solution
from langchain.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, SystemMessagePromptTemplate
from langchain_community.chat_models import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from llama_index import ServiceContext

# LlmaIndex manages data and embeddings 
from llama_index import VectorStoreIndex
from llama_index.retrievers import VectorIndexRetriever
from llama_index.query_engine import RetrieverQueryEngine
from llama_index.postprocessor import SimilarityPostprocessor
# lower level functions for creating nodes 
from llama_index.schema import TextNode, NodeRelationship, RelatedNodeInfo


def get_filenames_in_directory(directory_path):
    # List to store filenames
    filenames = []
    filepathnames = []

    # Iterate over all entries in the directory
    for entry in os.listdir(directory_path):
        # Get the full path
        full_path = os.path.join(directory_path, entry)

        # Check if it's a file and add to the list
        if os.path.isfile(full_path) and entry[0] != '.' and entry.split('.')[-1] == 'pdf':
            filenames.append(entry)
            filepathnames.append(full_path)

    return filenames, filepathnames

def most_common_header(list_of_lists):
    count_dict = {}
    for lst in list_of_lists:
        # Convert list to tuple for hashing
        tuple_version = tuple(lst[1])
        if tuple_version in count_dict:
            count_dict[tuple_version] += 1
        else:
            count_dict[tuple_version] = 1

    # Find the tuple with the maximum count
    most_common = max(count_dict, default=None, key=count_dict.get)

    # Convert tuple back to list
    return list(most_common)

def most_frequent_integer(int_list):
    if not all(isinstance(x, int) for x in int_list):
        raise ValueError("The list must contain only integers")

    frequency = {}
    for num in int_list:
        if num in frequency:
            frequency[num] += 1
        else:
            frequency[num] = 1

    most_frequent = None
    max_frequency = 0

    for num, freq in frequency.items():
        if freq > max_frequency:
            most_frequent = num
            max_frequency = freq

    return most_frequent

def string_to_list(string):
    try:
        result = ast.literal_eval(string)
        if isinstance(result, list):
            return result
        else:
            raise ValueError("The evaluated expression is not a list")
    except Exception as e:
        raise ValueError(f"Error converting string to list: {e}")

def extract_text_within_brackets(input_string):
    # Define the regex pattern to find text within square brackets
    pattern = r'\[(.*?)\]'

    # Use re.findall() to find all occurrences in the string
    matches = re.findall(pattern, input_string)

    # Handling multiple matches - here, returning all of them
    return matches

def get_firstpage_tables_as_list(doc=None):

    if not(doc):
        raise ValueError("fitz document not set - get_firstpage_tables_as_list")

    # focus on the first page 
    table_strategy = 'lines'
    tbls = doc[0].find_tables(vertical_strategy='lines', horizontal_strategy='lines')
    if len(tbls.tables) ==0: # did not find tables by grid, try spaces 
        tbls = doc[0].find_tables(vertical_strategy='text', horizontal_strategy='text')
        table_strategy = 'text'

    # merge the tables 
    tbl_out = []
    col_counts = []

    for tbl in tbls.tables:
        tbl_out.extend(tbl.extract())
        col_counts.append(tbl.col_count)

    col_count = most_frequent_integer(col_counts)

    return tbl_out, col_count, table_strategy

def best_header_word_match(header_word, header_words):
    # Initial check for null string
    if not header_word:
        return None
    
    # find the best match from header_words 
    tmp = {n:SequenceMatcher(a=header_word.lower(), b=hd.lower()).ratio() for n,hd in enumerate(header_words)}
    header_word_key = max(tmp, key=tmp.get)
    match_value = tmp[header_word_key]
    header_word_key = max(tmp, key=tmp.get)
    match_header_word = header_words[header_word_key]

    return match_header_word

#%%
load_dotenv()

# NOTE: for local testing only, do NOT deploy with your key hardcoded
tmp = os.getenv('OPENAI_API_KEY')
os.environ["OPENAI_API_KEY"] = tmp
# print(tmp)

dirpath = '../pdffiles'
filenames, filepath = get_filenames_in_directory(dirpath)

# define a list of header words from the docs 
header_words = ['Product', 'Variety', 'Size', 'Colour', 'Order Qty', 'Cost', 'Description', 'Code', 'Name',\
                'Category','Your Price', 'Price', 'Status', 'Zone', 'Catalog $', 'Pots/Tray', 'Amount',\
                'WH', 'Botanical Name', 'E-LINE', 'Available','Order', 'Total', 'PIN', 'UPC','Latin Name',\
                'Available Units','QTY', 'Notes','Avail QTY','Order Qty','Plant Name','Common Name','Sale Price',\
                'Pot Size','List','Net','Comments','AVL','Sku','Case Qty','Packaging', "Pots Ordered", 'SIZE 1', 'SIZE 2']

#%%
# define embedding model 
service_context = ServiceContext.from_defaults(embed_model="local")

# define the dict to save headers 
file_table_header = {}

# loop the files, and store as vectors 
for filename in filenames:
    print(f'\n{filename} at {datetime.now():%b %d %I:%M %p}')
    filetoken = filename.split('.')[0].replace(' ', '')

    # read the doc and get the tables from the first page  
    doc = fitz.open(f'{dirpath}/{filename}')

    tmp, numcols, tbl_strategy = get_firstpage_tables_as_list(doc)

    # get the best guess at the header row
    if len(tmp) > 0:
        # create a list of text nodes with one node per row in tmp 
        table_nodes = [TextNode(text=f"'{t}'", id_=n) for n,t in enumerate(tmp)]
        # table_nodes = [TextNode(t, id_=n) for n,t in enumerate(tmp)]
        table_index = VectorStoreIndex(table_nodes)

        # create the query engine with custom config to return just one node
        # https://docs.llamaindex.ai/en/stable/module_guides/deploying/query_engine/root.html#query-engine 
        query_engine = table_index.as_query_engine(
            similarity_top_k=1,
            vector_store_query_mode="default",
            alpha=None,
            doc_ids=None,
        )
        response = query_engine.query(\
        f"Retrieve column headings as a python list for a product price sheet with {numcols} columns ")
        header_rownum = int(response.source_nodes[0].id_)
        header_node_text = response.source_nodes[0].text
        header_raw = tmp[header_rownum]

        # match to header_word list 
        header_guess = [best_header_word_match(word, header_words) for word in tmp[int(response.source_nodes[0].id_)]]

        # save the file header info
        file_table_header[filetoken] = {'filename': filename,
                                        'header_rownum':header_rownum,
                                        'header_guess':header_guess, 
                                        'header_raw':header_raw, 
                                        'header_node_text':header_node_text}

        # debug and logging 
        print(#response.source_nodes[0].id_, '\n',
              # response.source_nodes[0].text,'\n',
              tmp[int(response.source_nodes[0].id_)], '\n',
              header_guess)
        
        # merge with the table from the first page 
        file_table = {filetoken:[dict(zip(header_guess,row)) for row in tmp[header_rownum+1:]]}
        
        # add the rest of the pages 
        for pagenum in range(1,doc.page_count):
            tbls = doc[pagenum].find_tables(vertical_strategy=tbl_strategy, horizontal_strategy=tbl_strategy)
            tbl_page = [row for tbl in tbls.tables for row in tbl.extract() if row != header_raw]
            # tbl_list_of_dicts = [dict(zip(header_guess,row)) for row in tbl_page]
            file_table[filetoken].extend([dict(zip(header_guess,row)) for row in tbl_page])

        jnk=0
    else:
        print('No table found with fitz parse by grid or text ')

    jnk = 0 # for debug
    print(f"Done at {datetime.now():%b %d %I:%M %p}")

jnk = 0 # for debug 

print(f"\n\nDone all at {datetime.now():%b %d %I:%M %p}")

print([len(x) for x in file_table])
