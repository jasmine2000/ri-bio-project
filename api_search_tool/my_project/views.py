import requests, json
from django.shortcuts import render
from django.http import HttpResponse

import pandas as pd
import xlsxwriter
import io
from pandas import json_normalize
from .forms import SearchForm

# currently unused
from fuzzywuzzy import fuzz
from fuzzywuzzy import process

cols = ["NCTId", "Sponsor", "Institution", "AuthorNames", "Role", "InterventionName", "Keyword", "BriefSummary"]

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
            fields = ['author', 'institution', 'sponsor', 'city', 'state', 'keyword']
            entries = {}
            for field in fields:
                entry = form.cleaned_data[field]
                if entry:
                    entries[field] = entry

            ct_df = get_ct_df(entries)
            # lens_df = get_lens_df(entries)
            nih_df = get_nih_df(entries)

            xlsx = create_xlsx(ct_df, nih_df)
            # xlsx = create_xlsx(ct_df, lens_df, nih_df)

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

# def create_xlsx(ct_df, lens_df, nih_df):
def create_xlsx(ct_df, nih_df):
    '''Write dataframe to xlsx file.

    arguments:
    df -- populated dataframe

    '''
    xlsx = io.BytesIO()
    PandasWriter = pd.ExcelWriter(xlsx, engine='xlsxwriter')
    ct_df.to_excel(PandasWriter, sheet_name='clinical_trials_results')
    # lens_df.to_excel(PandasWriter, sheet_name='lens_results')
    nih_df.to_excel(PandasWriter, sheet_name='nih_results')
    PandasWriter.save()

    xlsx.seek(0)

    return xlsx

# CLINCICAL TRIALS
def get_ct_df(entries):
    field_names = ["NCTId", "LeadSponsorName", "OverallOfficialAffiliation", 
                    "OverallOfficialName", "OverallOfficialRole", "InterventionName", 
                    "LocationCity", "LocationState", "Keyword", "BriefSummary"]

    response_json = make_ct_request(entries, field_names)
    ct_df = ct_json_to_df(response_json, field_names)
    return ct_df

def make_ct_request(entries, field_names):
    '''Generate a clinicaltrials.gov URL.

    arguments:
    expr -- raw keyword inputs (ex: "brown university, tumor")
    field_names -- global variable that defines the columns to return

    '''
    url = "https://clinicaltrials.gov/api/query/study_fields?"
    
    expr = "expr="

    search_terms = [f"%22{v.replace(' ', '+')}%22" for v in entries.values()]
    expr += 'AND'.join(search_terms)
    expr += '+AND+AREA%5BResultsFirstPostDate%5DRANGE%5B01/01/2000, MAX%5D'

    # ct_translator = {'author': 'OverallOfficialName', 
    #                 'institution': 'OverallOfficialAffiliation',
    #                 'sponsor': 'LeadSponsorName'}

    # for key, val in entries.items():
    #     search_terms.append(f'AREA%5B{ct_translator[key]}%5D"{val}"')

    # search_terms.append('AREA%5BResultsFirstPostDate%5DRANGE%5B01/01/2000, MAX%5D')
    # expr = '+AND+'.join(search_terms)

    fields = "fields="
    fields += "%2C".join(field_names)

    params = "min_rnk=1&max_rnk=1000&fmt=json"
    complete_url = f"{url}{expr}&{fields}&{params}"

    response_json = requests.get(complete_url).json()

    return response_json

def ct_json_to_df(response_json, field_names):
    '''Put response data into a dataframe.

    arguments:
    response -- json response from API
    field_names -- global variable that defines the columns

    '''
    ct_df = json_normalize(response_json['StudyFieldsResponse']['StudyFields'])

    def brackets(column):
        '''Convert columns from list of strings to plaintext.

        arguments:
        expr -- raw keyword inputs (ex: "brown university, tumor")
        field_names -- global variable that defines the columns to return

        '''
        column = column.replace("[", "")
        column = column.replace("]", "")
        column = column.replace("'", "")
        column = column.replace('"', '')
        return column

    for col in field_names:
        ct_df[col] = ct_df[col].astype(str)
        ct_df[col] = ct_df[col].apply(brackets)

    rename_dict = {}
    for init, final in zip(field_names, cols):
        if init != final:
            rename_dict[init] = final

    ct_df.rename(columns=rename_dict)
    ct_df.drop(['Rank'], axis=1)

    return ct_df


# LENS
def get_lens_df(entries):
    response_json = make_lens_request(entries)
    lens_df = lens_json_to_df(response_json)
    return lens_df

def make_lens_request(entries):
    key = 'qfqStKI9asHygnOGzGvvTM9M7gSd46HV4GYIQr94SN9Sg9Kn48sl'
    url = 'https://api.lens.org/scholarly/search'

    query = {"must":[]}
    years = {"range": {
                "year_published": {
                    "gte": "2000",
                    "lte": "2021"}
                }}
    query["must"].append(years)

    for key, val in entries.items():
        query["must"].append({"match_phrase": {"full_text": val}})

    boolean = {"bool": query}
    data_dict = {"query": boolean, 
            # "size": 1000, 
            "include": ["clinical_trials", "authors", "chemicals", "keywords", "abstract"]}
    data_json = json.dumps(data_dict)

    headers = {'Authorization': key, 'Content-Type': 'application/json'}
    response = requests.post(url, data=data_json, headers=headers)
    if response.status_code != requests.codes.ok:
        return response.status_code
    else:
        return json.loads(response.text)

def lens_json_to_df(response_json):
    all_data = response_json['data']
    
    response_fields = ["clinical_trials", "authors", "chemicals", "keywords", "abstract"]
    cols = ["Institution", "AuthorNames", "Role", "InterventionName", "Keyword", "BriefSummary"]

    entries = []
    for entry in all_data:
        entry_dict = {col: "" for col in cols}
        for field in response_fields:
            try:
                data = entry[field]
            except:
                continue
            keys, values = clean_lens_data(field, data)
            for key, val in zip(keys, values):
                entry_dict[key] = val

        entries.append(entry_dict)

    df = pd.DataFrame(entries)
    return df

def clean_lens_data(field, data):
    keys = []
    values = []
    names = {'abstract': 'BriefSummary', 'keywords': 'Keyword', 'chemicals': 'InterventionName'}

    if field == "authors":
        first_names = [author['first_name'] if 'first_name' in author else "" for author in data]
        last_names = [author['last_name'] if 'last_name' in author else "" for author in data]
        nested_affs = [[a['name'] for a in author['affiliations']] for author in data if 'affiliations' in author]

        names = [first + " " + last for first, last in zip(first_names, last_names)]
        affs = [name for aff in nested_affs for name in aff]

        keys += ['AuthorNames', 'Institution']
        values += [names, affs]

    else:
        keys.append(names[field])
        if field == 'chemicals':
            interventions = [chemical['substance_name'] for chemical in data]
            values.append(interventions)
        else:
            values.append(data)
    
    values = [', '.join(map(str, list(set(val)))) for val in values if type(val) != str]
    
    return keys, values


# NIH
def get_nih_df(entries):
    response_json = make_nih_request(entries)
    nih_df = nih_json_to_df(response_json)
    return nih_df

def make_nih_request(entries):
    url = 'https://api.reporter.nih.gov/v1/projects/Search'
    criteria = {
        "useRelevance": True,
        "includeActiveProjects": True,
        "projectStartDate": {
            "fromDate": "2000-01-01",
            "toDate": "2021-04-20"
        },
    }

    additional = {
        "includeFields": [
            "ApplId", "ProjectNum", "OrgName", "OrgCity", "OrgState", "ContactPiName", "AllText", "FullStudySection"],
        "offset": 0
        }

    translator = {'author': 'piNames', 'institution': 'orgNames', 'city': 'orgCities', 'state': 'orgStates', 'keyword': 'terms'}

    for key, val in entries.items():
        if key == 'author':
            val = {'anyName': val}
        criteria[translator[key]] = [val]

    data_dict = {"criteria": criteria}
    data_dict.update(additional)
    data_json = json.dumps(data_dict)

    headers = {'accept': 'application/json', 'Content-Type': 'application/json'}
    response = requests.post(url, data=data_json, headers=headers)
    if response.status_code != requests.codes.ok:
        return response.status_code
    else:
        return json.loads(response.text)


def nih_json_to_df(response_json):
    results = response_json['results']
    rows = []
    columns = ['appl_id', 'project_title', 'investigators', 'org_name', 'org_loc', 'keywords', 'abstract_text']
    for result in results:
        row = {}
        for col in columns:
            try:
                row[col] = result[col]
            except KeyError:
                row[col] = None
        
        people = result['principal_investigators']
        people_entry = ""
        for p in people:
            people_entry += f"{p['full_name']}, "
        row['investigators'] = people_entry[:-2]

        row['org_loc'] = f"{result['org_city']}, {result['org_state']}"
        
        all_terms = set()
        for t in 'terms', 'pref_terms':
            if result[t] is not None:
                terms = result[t].split(';')
                terms = set([t.strip() for t in terms])
                all_terms.update(terms)

        all_terms = [term for term in list(all_terms) if len(term) > 0]

        terms_string = ", ".join(all_terms)
        row['keywords'] = terms_string

        if row['abstract_text'] is not None:
            row['abstract_text'] = row['abstract_text'].strip('\r\n')

        rows.append(row)

    df = pd.DataFrame.from_dict(rows)
    return df


# RETURNS CLAIMS OF A PATENT
def lens_patent_request(request):
    '''Gets claims from lens id(s).

    arguments from form:
    search_term -- term(s) to use for query
    
    '''
    if request.method == 'POST': # user has submitted data
        form = SearchForm(request.POST)
        if form.is_valid():
            search_input = form.cleaned_data['search_term']
            lens_response = lens_request(search_input)
            if lens_response.status_code != requests.codes.ok:
                return(lens_response.status_code)
            else:
                response_body = parse_claim_text(lens_response.text)
                response = HttpResponse(
                    response_body,
                    content_type='text/html; encoding=utf8'
                )
                
                return response
            
    else: # show empty form
        form = SearchForm()

    return render(request, 'lens.html', {'form': form})

def lens_request(search_input):
    lens_ids = comma_parser(search_input)

    url = 'https://api.lens.org/patent/search'
    data_dict = {
                "query": {
                    "terms":  {
                        "lens_id": lens_ids
                    }
                },
                "size": 100,
                "include": ["claims"],
                "scroll": "1m",
                "scroll_id": ""
            }
    data = json.dumps(data_dict)
    headers = {'Authorization': lens_key, 'Content-Type': 'application/json'}
    response = requests.post(url, data=data, headers=headers)
    return response

def parse_claim_text(response_text):
    json_data = json.loads(response_text)
    response_body = []

    for result in json_data['data']:
        lens_id = result['lens_id']
        response_body.append(f'<h2>{lens_id}</h2>')
        full_list = result['claims']
        for entry in full_list:
            if entry['lang'] == 'en':
                all_claims = entry['claims']
                for claim in all_claims:
                    text = claim['claim_text'][0]
                    response_body.append(f'<p>{text}</p>')

    response_body.append('</html></body>')
    return response_body

def comma_parser(search_input):
    phrases = search_input.split(',')
    final_phrases = []
    for phrase in phrases:
        phrase = phrase.strip()
        if len(phrase) > 0:
            final_phrases.append(phrase)

    return phrases


def index(request):
    return HttpResponse("index")