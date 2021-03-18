import os.path
import re
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


def parse_cpc_uspc(line):
    i_loc = []
    for i in range(len(line)):
        if line[i] == 'I':
            i_loc.append(i)
    
    for i in i_loc:
        line = line[:i] + '1' + line[i + 1:]

    def process(substr):
        i = substr.index('.')
        while True:
            if substr[i] == '.':
                i += 1
            else:
                break
        
        substr = substr[i:]
        substr = substr.strip()
        return substr

    i_uspc = line.index('USPC')
    cpc = process(line[:i_uspc])
    cpc = cpc.split('; ')
    new_cpc = []
    for c in cpc:
        spl = c.split(" ")
        length = len(spl[0])
        if length == 4:
            new_cpc.append(spl[0] + " " + spl[1])
        else:
            s = 4 - length
            new_cpc.append(spl[0] + spl[1][:s] + " " + spl[1][s:])
    
    uspc = process(line[i_uspc:])
    new_uspc = parse_uspc(uspc)
    return new_cpc, new_uspc


def parse_uspc(line):
    # p = re.compile(r'\d{3}/{1}\d{1,3}\d*\W*\d{0,2}') # trying to match whole thing
    p = re.compile(r'\d{3}/{1}\d{1,3}')
    a = p.findall(line)
    indices = []
    for i in a:
        indices.append(line.index(i))
    new_uspc = []
    for i in range(len(indices)):
        u_1 = indices[i]
        if i == len(indices) - 1:
            u_2 = len(line)
        else:
            u_2 = indices[i + 1]

        e = line[u_1:u_2]
        e = e.strip(" ;")
        new_uspc.append(e)

    return new_uspc


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


def parse_doc(terms, path_to_pdf):
    patent_pdf = open(path_to_pdf, 'rb')
    text = extract_text(patent_pdf)

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
            elif p == 'Assignees' or p == 'Inventors' or p == 'CPC':
                start = 0

            entry, index = get_element(i, count, start)
            relevant_information[p] = entry
            i = index

            terms.remove(p)
        
        else:
            i += 1

    new_info = {}
    for key, value in relevant_information.items():
        if key == 'CPC':
            cpc, uspc = parse_cpc_uspc(value)
            new_info['CPC'] = cpc
            new_info['USPC'] = uspc
        else:
            new_info[key] = parse_entries(key, value)
    

    return new_info


if __name__ == '__main__':

    # text = extract_text('./patent_files/patent_ex_02.pdf')
    # two = open('patent_02.txt', 'w+')
    # two.write(text)

    terms = ['Int. Cl.', 'Inventors', 'CPC', 'Assignees']
    path_to_pdf = './patent_files/patent_ex_01.pdf'

    relevant_information = parse_doc(terms, path_to_pdf)
    print(relevant_information)


