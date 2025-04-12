# %%
import csv
import glob
import re
import string
import sys
import time
import numpy as np
import os
import collections
import pandas as pd
from bs4 import BeautifulSoup

import Load_MasterDictionary as LM
import lm_neg_wordlist
import harvard_wordlist

# User defined directory for files to be parsed
TARGET_FILES = r'./index_files'
# User defined file pointer to LM dictionary
MASTER_DICTIONARY_FILE = r'Loughran-McDonald_MasterDictionary_1993-2024.csv'
# User defined output file
OUTPUT_FILE = r'Parser.csv'
# Setup output
OUTPUT_FIELDS = ['file name,', 'file size,', 'number of words,', '% positive,', '% negative,',
                 '% uncertainty,', '% litigious,', '% modal-weak,', '% modal moderate,',
                 '% modal strong,', '% constraining,', '# of alphabetic,', '# of digits,',
                 '# of numbers,', 'avg # of syllables per word,', 'average word length,', 'vocabulary']
# CLEANED_PATH = './cleaned'

lm_dictionary = LM.load_masterdictionary(MASTER_DICTIONARY_FILE, True)
lm_neg_list = [v for k,v in vars(lm_neg_wordlist).items() if isinstance(v, list) and not k.startswith('__')][0]
harvard_neg_list = []
#harvard_neg_list = [v for k,v in vars(harvard_wordlist).items() if isinstance(v, list) and not k.startswith('__')][0]
with open('Harvard IV_Negative Word List_Inf.txt', 'r', encoding='utf-8') as f:
    harvard_neg_list = [line.strip() for line in f if line.strip()] 

print(len(lm_neg_list))
print(len(harvard_neg_list))

# Calculate TF/IDF matrix
def update_tf_idf_matrix(frequencies,fileIndex,wordList,tf_matrix,idf_matrix,doc_length_matrix):
    totalWordsNum = sum(frequencies.values())
    for word, freq in frequencies.items():
        wordIndex = wordList.index(word)
        tf_matrix[fileIndex, wordIndex] = freq # the raw count of the (wordIndex)th word in the (fileIndex)th document
        idf_matrix[fileIndex, wordIndex] = 1 # 1 -> The file contents the word
            
    doc_length_matrix[fileIndex, 0] = totalWordsNum # To help calculate the average words in one doc later

def get_file_content(file_path):
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        raw_text = f.read()
    
    # Only use the TEXT parts
    match = re.search(r'<TEXT>.*?</TEXT>', raw_text, re.DOTALL)
    if match:
        content = match.group(0)
    else:
        content = raw_text
    
    # Remove html/xml
    soup = BeautifulSoup(content, 'html.parser')
    plain_text = soup.get_text(separator=' ')

    textContent = plain_text.upper()
    textContent = re.sub(r'<[^>]*?>', ' ', textContent)
    # textContent = re.sub(r'(?<=[0-9])[.,](?=[0-9])', '', textContent)
    textContent = re.sub(r'[^A-Z\s]', ' ', textContent)
    textContent = textContent.translate(str.maketrans(string.punctuation, " " * len(string.punctuation)))
    textContent = re.sub(r'\s+', ' ', textContent).strip()
    
    return str(textContent)


# %%
def process_edgar_file(is_lm = True):
    #wordList = [item for item in lm_dictionary if item.negative ]
    if is_lm:
        wordList = lm_neg_list
    else:
        wordList = harvard_neg_list
    wordsNum = len(wordList)

    fileNum = 0
    for root, dirs, files in os.walk(TARGET_FILES):
        for file in files:
            if file.lower().endswith('.txt'): 
                fileNum += 1

    print(fileNum)
    
    tf_matrix = np.zeros((fileNum, wordsNum)) # occurrence frequency, size = #of documents * # of negative words in lm_dictionary)
    idf_matrix = np.zeros((fileNum, wordsNum)) # whether this word appeared in the txt files
    doc_length_matrix = np.zeros((fileNum, 1)) # the number of words in a file
    
    meta_list = []
    namePattern = re.compile(r"(\d{8})_10-[QK]_edgar_data_(\d{4,7})_(\d{10})") 

    # Get each file and calculate word frequency
    fileIndex = 0
    for root, dirs, files in os.walk(TARGET_FILES):
        for file in files:
            file_path = os.path.join(root, file)
            textContent = get_file_content(file_path)
            words = textContent.split()

            # Parse to obtain and save the cik and release date.
            parseRes = namePattern.search(file)
            if parseRes:
                currFileDate = parseRes.group(1)
                cik = parseRes.group(2)
                cik = str(cik).zfill(10)
                meta_list.append({
                    'filename': file,
                    'cik': cik,
                    'date': pd.to_datetime(currFileDate)
                })

                wordCount = collections.Counter(words)
                frequencies = {}
                for word in wordList:
                    if word in wordCount:
                        frequencies[word] = wordCount[word]
                        
                # Update the matrix about the current file
                totalWordsNum = sum(frequencies.values())
                for word, freq in frequencies.items():
                    wordIndex = wordList.index(word)
                    # print(wordIndex)
                    tf_matrix[fileIndex, wordIndex] = freq # the raw count of the (wordIndex)th word in the (fileIndex)th document
                    idf_matrix[fileIndex, wordIndex] = 1 # 1 -> The file contents the word
                
                # print(np.sum(idf_matrix, axis=0))
                doc_length_matrix[fileIndex, 0] = totalWordsNum # To help calculate the average words in one doc later

                fileIndex += 1

                print("\nFinish parsing: " + str(fileIndex) + file_path )
            else:
                print("\n Error when parsing file name:",file)
                continue


    # Calculate the final results of tfidf_matrix
    doc_freq = np.sum(idf_matrix, axis=0)
    # IDF part: log(N / df_i)
    idf_values = np.log(fileNum / (1 + doc_freq))
    # get log(tf + 1) numerator
    tf_numer = 1 + np.log(tf_matrix, where=tf_matrix > 0, out=np.zeros_like(tf_matrix))
    log_doc_length = 1 + np.log(doc_length_matrix + 1e-8)

    # Apply IDF to the tf matrix to get tf-idf and term_weight
    tfidf_matrix = tf_matrix * idf_values
    
    term_weight = (tf_numer / log_doc_length) * idf_values[np.newaxis, :] 
    term_weight[tf_matrix == 0] = 0

    final_tfidf = np.sum(tfidf_matrix, axis=1, keepdims=True)
    final_weight = np.sum(term_weight, axis=1, keepdims=True)
    df = pd.DataFrame(meta_list)
    df['tfidf_value'] = final_tfidf
    df['term_weight'] = final_weight
    df.to_csv('harvard_term_weight_results_new.csv', index=False)

    print("Finished calculating TFIDF and term weight.")
    return final_tfidf, final_weight

# %%
if __name__ == '__main__':
    print('\nStart running Generic_Parser.py\n')
    # tfidf_matrix, term_weight = process_edgar_file(True)
    tfidf_matrix, term_weight = process_edgar_file(False)
    print("tfidf_matrix:\n",tfidf_matrix)
    print("\n term_weight:\n",term_weight)
    print('\nNormal termination.')


