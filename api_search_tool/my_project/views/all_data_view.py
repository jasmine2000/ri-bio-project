import requests, json
from django.shortcuts import render
from django.http import HttpResponse

import pandas as pd
import xlsxwriter
import io
import us
from pandas import json_normalize
from ..forms import SearchForm

from .ct_view import *
from .lens_s_view import *

# currently unused
from fuzzywuzzy import fuzz
from fuzzywuzzy import process

cols = ["NCTId", "Sponsor", "Institution", "AuthorNames", "Role", "InterventionName", "Keyword", "BriefSummary"]
state_to_abbrev = {'Alabama': 'AL', 'Alaska': 'AK', 'American Samoa': 'AS', 'Arizona': 'AZ', 'Arkansas': 'AR', 'California': 'CA', 'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE', 'District of Columbia': 'DC', 'Florida': 'FL', 'Georgia': 'GA', 'Guam': 'GU', 'Hawaii': 'HI', 'Idaho': 'ID', 'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA', 'Kansas': 'KS', 'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME', 'Maryland': 'MD', 'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN', 'Mississippi': 'MS', 'Missouri': 'MO', 'Montana': 'MT', 'Nebraska': 'NE', 'Nevada': 'NV', 'New Hampshire': 'NH', 'New Jersey': 'NJ', 'New Mexico': 'NM', 'New York': 'NY', 'North Carolina': 'NC', 'North Dakota': 'ND', 'Northern Mariana Islands': 'MP', 'Ohio': 'OH', 'Oklahoma': 'OK', 'Oregon': 'OR', 'Pennsylvania': 'PA', 'Puerto Rico': 'PR', 'Rhode Island': 'RI', 'South Carolina': 'SC', 'South Dakota': 'SD', 'Tennessee': 'TN', 'Texas': 'TX', 'Utah': 'UT', 'Vermont': 'VT', 'Virgin Islands': 'VI', 'Virginia': 'VA', 'Washington': 'WA', 'West Virginia': 'WV', 'Wisconsin': 'WI', 'Wyoming': 'WY'}

def publications_request(request):
    '''Queries information from clinicaltrials.gov API and lens.org API.

    arguments from form:
    
    used in both CT and Lens:
        author, institution, keyword
    used only in CT:
        sponsor
    
    '''
    if request.method == 'POST': # user has submitted data
        form = SearchForm(request.POST)
        if form.is_valid():
            fields = ['author', 'institution', 'sponsor', 'city', 'state', 'keyword', 'lens_id']
            entries = {}
            for field in fields:
                entry = form.cleaned_data[field]
                if entry:
                    entries[field] = entry

            ct_df = get_ct_df(entries)
            lens_s_df = get_lens_s_df(entries)
            lens_p_df = get_lens_p_df(entries)
            nih_df = get_nih_df(entries)

            xlsx = create_xlsx(ct_df, lens_s_df, lens_p_df, nih_df)

            filename = 'query_results.xlsx'
            response = HttpResponse(
                xlsx,
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = 'attachment; filename=%s' % filename

            return response
            
    else: # show empty form
        form = SearchForm()

    return render(request, 'search.html', {'form': form})

def create_xlsx(ct_df, lens_s_df, lens_p_df, nih_df):
# def create_xlsx(ct_df, nih_df):
    '''Write dataframe to xlsx file.

    arguments:
    df -- populated dataframe

    '''
    xlsx = io.BytesIO()
    PandasWriter = pd.ExcelWriter(xlsx, engine='xlsxwriter')
    ct_df.to_excel(PandasWriter, sheet_name='clinical_trials_results')
    lens_s_df.to_excel(PandasWriter, sheet_name='lens_s_results')
    lens_p_df.to_excel(PandasWriter, sheet_name='lens_p_results')
    nih_df.to_excel(PandasWriter, sheet_name='nih_results')
    PandasWriter.save()

    xlsx.seek(0)

    return xlsx


# LENS PATENT
def get_lens_p_df(entries):
    response_json = make_lens_p_request(entries)
    lens_p_df = lens_p_json_to_df(response_json)
    return lens_p_df

def make_lens_p_request(entries):
    url = 'https://api.lens.org/patent/search'

    query = {"must":[]}
    years = {"range": {
                "year_published": {
                    "gte": "2000"}
                }}
    query["must"].append(years)

    field_dict = {'keyword': ["title", "claims", "description"],
                  'author': ["inventor.name", "owner_all.name", "description"],
                  'institution': ["applicant.name", "owner_all.name", "description"],
                  'sponsor': ["applicant.name", "owner_all.name", "description"],
                  'city': ["applicant.address", "inventor.address", "owner_all.address"],
                  'state': ["applicant.address", "inventor.address", "owner_all.address"]}
    try:
        lensid = entries['lens_id']
        query["must"].append({"terms": {'lens_id': [lensid]}})
    except KeyError:
        for key, val in entries.items():
            query_string = {
                "query_string": {
                    "query": val,
                        "fields": field_dict[key],
                        "default_operator": "or"
                    }
                }
            query["must"].append(query_string)

    boolean = {"bool": query}
    data_dict = {"query": boolean, 
            "size": lens_size, 
            "include": ["lens_id", "biblio", "description", "claims"]}

    data = json.dumps(data_dict)
    headers = {'Authorization': lens_key, 'Content-Type': 'application/json'}
    response = requests.post(url, data=data, headers=headers)
    if response.status_code != requests.codes.ok:
        return response.status_code
    else:
        return json.loads(response.text)

def lens_p_json_to_df(response_json):
    rows = []
    for result in response_json['data']:
        rows.append(parse_lens_p(result))
    df = pd.DataFrame.from_dict(rows)
    return df

def parse_lens_p(result):
    row = {}
    row['lens_id'] = result['lens_id']

    bib = result['biblio']
    parties = bib['parties']

    titles = bib['invention_title']
    for title in titles:
        if title['lang'] == 'en':
            row['title'] = title['text']
            break

    fields = {
        'inventors': 
            {'extracted_name': 'inventors'}, 
        'owners_all': 
            {'extracted_name': 'owner', 
            'extracted_address': 'location'}
    }

    for field, field_dict in fields.items():
        for f in field_dict:
            try:
                ls = set()
                for entry in parties[field]:
                    value = entry[f]
                    if f == 'extracted_name':
                        value = value['value']
                    ls.add(value)
                ls_str = ', '.join(list(ls))
                row[field_dict[f]] = ls_str
            except KeyError:
                row[field_dict[f]] = ""

    for string in ['ipcr', 'cpc']:
        try:
            section = bib['classifications_' + string]
            section_ls = []
            for c in section['classifications']:
                section_ls.append(c['symbol'])
            section_str = ', '.join(section_ls)
            row[string] = section_str
        except KeyError:
            row[string] = ""

    try:
        full_list = result['claims']
        for entry in full_list:
            if entry['lang'] == 'en':
                all_claims = entry['claims']
                full_text = ""
                for claim in all_claims:
                    claim_text = claim['claim_text'][0]
                    if "(canceled)" in claim_text:
                        continue
                    full_text += claim_text + " "
                row['claims'] = full_text
    except KeyError:
        row['claims'] = ""

    return row


# NIH
def get_nih_df(entries):
    try:
        del entries['lens_id']
    except KeyError:
        pass
    response_json = make_nih_request(entries)
    nih_df = nih_list_to_df(response_json)
    return nih_df

def make_nih_request(entries):
    url = 'https://api.federalreporter.nih.gov/v1/Projects/search'

    query_string = '?query='
    queries = []

    if 'keyword' in entries:
        keyword = entries['keyword']
        queries.append(f'text%3A{keyword}%24textFields%3Aterms')

    translator = {'author': 'piName', 'institution': 'orgName', 'state': 'orgState'}
    for key, val in entries.items():
        try:
            new_val = val.replace(' ', '%20')
            queries.append(f'{translator[key]}%3A{new_val}')
        except KeyError:
            continue

    fiscal_years = ','.join(str(x) for x in range(2000, 2022))
    queries.append(f'fy:{fiscal_years}')

    query_string += '%24'.join(queries)

    complete_url = url + query_string
    response = requests.get(complete_url).json()

    all_items = []
    size = response['totalCount']
    items = response['items']
    all_items += items

    iterations = int(size/50)
    for i in range(iterations):
        new_url = complete_url + f'&offset={(i + 1)*50 + 1}'
        response = requests.get(new_url).json()
        items = response['items']
        all_items += items

    return all_items

def nih_list_to_df(all_items):
    rows = []
    columns = ['title', 'fy', 'smApplId', 'piNames', 'orgName', 'orgLoc', 'keywords', 'abstract']
    for result in all_items:
        row = {}
        for col in columns:
            try:
                row[col] = result[col]
            except KeyError:
                row[col] = None
        
        all_people = []
        people1 = result['contactPi']
        people2 = result['otherPis']
        for people in [people1, people2]:
            if people is None:
                continue
            cleaned = people.strip(' ;')
            for person in cleaned.split(';'):
                name = person.split(',')
                name = [n.strip() for n in name]
                all_people.append(f'{name[1]} {name[0]}')
            
        row['piNames'] = ', '.join(all_people)

        row['orgLoc'] = f"{result['orgCity']}, {result['orgState']}"
        
        all_terms = set()
        if result['terms'] is not None:
            terms = result['terms'].split(';')
            terms = set([t.strip() for t in terms])
            all_terms.update(terms)
        all_terms = [term for term in list(all_terms) if len(term) > 0]

        terms_string = ", ".join(all_terms)
        row['keywords'] = terms_string

        rows.append(row)

    df = pd.DataFrame.from_dict(rows)
    return df


def index(request):
    return HttpResponse("index")