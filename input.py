import os.path
from pathlib import Path
import pdfminer
from pdfminer.high_level import extract_text


from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer

def parse_line(line, keywords):
    counter = {keyword: 0 for keyword in keywords}
    i = 0
    while i < len(line):
        char = line[i]
        for key, val in counter.items():
            if val == len(key):
                return key
            elif key[val] == char:
                counter[key] += 1
            else:
                counter[key] = 0
        
        i += 1
    
    return None

def parse_entries(key, line):
    key = key + ':'
    i = 0
    while i < len(line):
        if line[i:i+len(key)] == key:
            line = line[i+len(key):]
            break
        i += 1

    line = line.strip()
    result_loc = line.split('; ')
    result = [r.split(',')[0] for r in result_loc]
    
    return result

def parse_inventors(line):
    i = 0
    while i < len(line):
        if line[i:i + 10] == 'Inventors:':
            line = line[i + 10:]
            break
        i += 1

    line = line.strip()
    inventors_loc = line.split('; ')
    inventors = [i.split(',')[0] for i in inventors_loc]
    
    return inventors

def parse_assignees(line):
    for i in range(len(line)):
        if line[i:i + 11] == 'Assignees: ':
            line = line[i + 11:]
            break

    assignees_loc = line.split('; ')
    assignees = [a.split(',')[0] for a in assignees_loc]
    
    return assignees

def parse_doc(terms, path_to_pdf):
    patent_pdf = open(path_to_pdf, 'rb')
    text = extract_text(patent_pdf)

    # paragraphs: {'Int. Cl.': 3, 'Inventors': 1, 'CPC', 'USPC', 'Assignees'}
    relevant_information = {}

    i = 0
    lines = text.splitlines()
    def get_element(line_number, paragraphs, start):
        entry = ""
        index = line_number + start
        paragraph_count = 1
        while paragraph_count < paragraphs + 1:
            next_line = lines[index]
            entry += next_line
            if len(next_line) == 0:
                paragraph_count += 1
            index += 1
        relevant_information[p] = entry
        return entry, index

    while i < len(lines):
        line = lines[i]
        if 'Sheet 1' in line or len(terms) == 0:
            break

        p = parse_line(line, terms)
        if p is not None:
            start = 1
            count = 1
            if p == 'Int. Cl.':
                count = 3
            elif p == 'Assignees' or p == 'Inventors':
                start = 0

            entry, index = get_element(i, count, start)
            relevant_information[p] = entry
            i = index

            terms.remove(p)
        
        else:
            i += 1

    # relevant_information['Inventors'] = parse_inventors(relevant_information['Inventors'])

    return relevant_information


if __name__ == '__main__':

    # text = extract_text('./patent_files/patent_ex_02.pdf')
    # two = open('patent_02.txt', 'w+')
    # two.write(text)

    # terms = ['Int. Cl.', 'Inventors', 'CPC', 'Assignees']
    # path_to_pdf = './patent_files/patent_ex_01.pdf'

    # relevant_information = parse_doc(terms, path_to_pdf)
    # for key in relevant_information:
    #     print(key + ": " + relevant_information[key])

    i = parse_entries('Assignees', "(73)  Assignees: RHODE ISLAND HOSPITAL, ")
    print(i)

