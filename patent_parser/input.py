import re
import pdfminer
from pdfminer.high_level import extract_text

# HELPER FUNCTIONS

def parse_for_keywords(line, keywords):
    '''
    Used during main loop of parse_doc to find key terms such as 'CPC'
    Short algorithm that iterates over line once, keeping track of consecutive matching letters

    example input:
        "(75)  Inventors:  Thomas J. Webster, Barrington, RI"
    output:
        "Inventors"

    '''
    counter = {keyword: 0 for keyword in keywords}
    i = 0
    while i < len(line):
        char = line[i]
        for key, val in counter.items():
            if val == len(key): # have found a match for all letters
                return key
            elif key[val] == char: # if the next letter matches, add to count/index
                counter[key] += 1
            else:
                counter[key] = 0 # letter doesn't match, reset counter
        
        i += 1
    
    return None


def parse_cpc_uspc(line):
    '''
    Takes in CPC input and outputs parsed CPC and USPC values
    Does some autocorrecting for values that are a little off

    example input: 
        "CPC ..............  CI2N 15/87 (2013.01); A61 K3I/713 
        (2013.01); A61K 47/48061 (2013.01); C12O 
        I/6841 (2013.01); C12N 15/115 (2013.01) 
        USPC ..........  514/44. A 435/375; 435/455; 435/471; 
        435/252.1435/6.11536/24.5"
    output:
        ['C12N 15/87', 'A61K 31/713', 'A61K 47/48061', 'C12O 1/6841', 'C12N 15/115']
        ['514/44. A', '435/375', '435/455', '435/471', '435/252.1', '435/6.11', '536/24.5']

    '''
    i_loc = []
    for i in range(len(line)):
        if line[i] == 'I':
            i_loc.append(i)
    
    for i in i_loc:
        line = line[:i] + '1' + line[i + 1:]

    def process(substr):
        '''
        CPC/USPC start with 'CPC ..............'- get rid of dots
        TODO: TRY USING .STRIP INSTEAD
        '''
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
    new_cpc = parse_cpc(cpc)
    
    uspc = process(line[i_uspc:])
    new_uspc = parse_uspc(uspc)
    return new_cpc, new_uspc


def parse_cpc(line):
    '''
    Called from parse_cpc_uspc

    example input: 
        "CI2N 15/87 (2013.01); A61 K3I/713 
        (2013.01); A61K 47/48061 (2013.01); C12O 
        I/6841 (2013.01); C12N 15/115 (2013.01) "
    output:
        ['C12N 15/87', 'A61K 31/713', 'A61K 47/48061', 'C12O 1/6841', 'C12N 15/115']
    '''
    cpc = line.split('; ')
    new_cpc = []
    for c in cpc:
        spl = c.split(" ")
        length = len(spl[0])
        if length == 4:
            new_cpc.append(spl[0] + " " + spl[1])
        else:
            s = 4 - length
            new_cpc.append(spl[0] + spl[1][:s] + " " + spl[1][s:])
    
    return new_cpc


def parse_uspc(line):
    '''
    Called from parse_cpc_uspc

    example input: 
        "514/44. A 435/375; 435/455; 435/471; 
        435/252.1435/6.11536/24.5"
    output:
        ['514/44. A', '435/375', '435/455', '435/471', '435/252.1', '435/6.11', '536/24.5']
    '''
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
    '''
    Parse function for Inventors and Assignees: these are usually seperated by ';' then ','

    example input: 
        "(75)  Inventors:  Thomas J. Webster, Barrington, RI 
        (US); Qian Chen, Barrington, RI (US); 
        Yupeng Chen, Mansfield, MA (US) "
    output:
        ['Thomas J. Webster', 'Qian Chen', 'Yupeng Chen']
    '''
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

        p = parse_for_keywords(line, terms)
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


