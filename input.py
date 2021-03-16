import PyPDF2
import pdfminer
from pdfminer.high_level import extract_text
from uspto_repo import uspto

data = uspto.read_and_parse_file_from_disk('patent_example_01.xml',['CLAS'],'xml4')
print(data)

# text = extract_text('./patent_files/patent_ex_01.pdf')
# print(repr(text))

# mypdf = open("./patent_files/patent_ex_01.pdf", mode='rb')
# pdf_document = PyPDF2.PdfFileReader(mypdf)

# first_page = pdf_document.getPage(0)

# print(first_page.extractText())
