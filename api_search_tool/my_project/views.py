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

field_names = ["NCTId", "LeadSponsorName", "OverallOfficialAffiliation", 
                    "OverallOfficialName", "OverallOfficialRole", "InterventionName", 
                    "Keyword", "BriefSummary"]

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
            author = form.cleaned_data['author']
            institution = form.cleaned_data['institution']
            sponsor = form.cleaned_data['sponsor']
            keyword = form.cleaned_data['keyword']

            url = get_url(author, institution, sponsor, keyword, field_names)
            json_response = requests.get(url).json()
            ct_df = cleaned_df(json_response, field_names)

            lens_df = get_lens_df(author, institution, keyword)

            xlsx = create_xlsx(ct_df, lens_df)

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


def comma_parser(search_input):
    phrases = search_input.split(',')
    final_phrases = []
    for phrase in phrases:
        phrase = phrase.strip()
        if len(phrase) > 0:
            final_phrases.append(phrase)

    return phrases


def get_url(author, institution, sponsor, keyword, field_names):
    '''Generate a clinicaltrials.gov URL.

    arguments:
    expr -- raw keyword inputs (ex: "brown university, tumor")
    field_names -- global variable that defines the columns to return

    '''
    url = "https://clinicaltrials.gov/api/query/study_fields?"
    
    expr = "expr="

    search_terms = []
    if keyword.lower() != 'none':
        search_terms.append(f'"{keyword}"')

    if author.lower() != 'none':
        search_terms.append(f'AREA%5BOverallOfficialName%5D"{author}"')

    if institution.lower() != 'none':
        search_terms.append(f'AREA%5BOverallOfficialAffiliation%5D{institution}')

    if sponsor.lower() != 'none':
        search_terms.append(f'AREA%5BLeadSponsorName%5D"{sponsor}"')

    for i,term in enumerate(search_terms):
        if i != 0:
            expr += '+AND+'
        expr += term

    fields = "fields="
    for f in field_names:
        fields += f"{f}%2C"

    fields = fields[:-3] # get rid of trailing %2C

    params = "min_rnk=1&max_rnk=200&fmt=json"
    complete_url = f"{url}{expr}&{fields}&{params}"

    return complete_url

def cleaned_df(response, field_names):
    '''Put response data into a dataframe.

    arguments:
    response -- json response from API
    field_names -- global variable that defines the columns

    '''
    df = json_normalize(response['StudyFieldsResponse']['StudyFields'])

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
        df[col]= df[col].astype(str)
        df[col] = df[col].apply(brackets)

    df.rename(columns={"LeadSponsorName": "Sponsor", 
                       "OverallOfficialAffiliation": "Institution", 
                       "OverallOfficialName": "AuthorNames",
                       "OverallOfficialRole": "Role"})

    return df

def create_xlsx(ct_df, lens_df):
    '''Write dataframe to xlsx file.

    arguments:
    df -- populated dataframe

    '''
    xlsx = io.BytesIO()
    PandasWriter = pd.ExcelWriter(xlsx, engine='xlsxwriter')
    ct_df.to_excel(PandasWriter, sheet_name='clinical_trials_results')
    lens_df.to_excel(PandasWriter, sheet_name='lens_results')
    PandasWriter.save()

    xlsx.seek(0)

    return xlsx


# lens stuff

lens_key = 'qfqStKI9asHygnOGzGvvTM9M7gSd46HV4GYIQr94SN9Sg9Kn48sl'

def get_lens_df(author, institution, keyword):
    key = 'qfqStKI9asHygnOGzGvvTM9M7gSd46HV4GYIQr94SN9Sg9Kn48sl'
    url = 'https://api.lens.org/scholarly/search'

    query = {"must":[]}
    if keyword.lower() != 'none':
        query["must"].append({"match_phrase": {"abstract": keyword}})

    if author.lower() != 'none':
        query["must"].append({"match_phrase": {"author.display_name": author}})

    if institution.lower() != 'none':
        query["must"].append({"match_phrase": {"author.affiliation.name": institution}})

    boolean = {"bool": query}
    data_dict = {"query": boolean, 
            "size": 200, 
            "include": ["clinical_trials", "authors", "chemicals", "keywords", "abstract"]}
    data_json = json.dumps(data_dict)

    headers = {'Authorization': key, 'Content-Type': 'application/json'}
    response = requests.post(url, data=data_json, headers=headers)
    if response.status_code != requests.codes.ok:
        return response.status_code
    else:
        full_response = json.loads(response.text)
        all_data = full_response['data']
        entries = get_data(all_data)

        df = pd.DataFrame(entries)
        return df

def get_data(all_data):
    response_fields = ["clinical_trials", "authors", "chemicals", "keywords", "abstract"]
    cols = ["NCTId", "Sponsor", "Institution", "AuthorNames", "Role", "InterventionName", "Keyword", "BriefSummary"]

    entries = []
    for entry in all_data:
        entry_dict = {col: "" for col in cols}
        for field in response_fields:
            try:
                data = entry[field]
            except:
                continue
            keys, values = clean_data(field, data)
            for key, val in zip(keys, values):
                entry_dict[key] = val

        entries.append(entry_dict)

    return entries

def clean_data(field, data):
    keys = []
    values = []

    if field == "clinical_trials":
        ids = ""
        for trial in data:
            ids += trial['id'] + ', '
        keys.append('NCTId')
        values.append(ids[:-2])

    elif field == "authors":
        names = []
        affiliations = []
        for author in data:
            name = ""
            if 'first_name' in author:
                name += author['first_name'] + " "
            if 'last_name' in author:
                name += author['last_name']
            
            names.append(name)
            if 'affiliations' in author:
                affiliation = author['affiliations']
                for aff in affiliation:
                    affiliations.append(aff['name'])

        names_str = ', '.join(map(str, names))
        aff_str = ', '.join(map(str, affiliations))
        keys += ['AuthorNames', 'Institution']
        values += [names_str, aff_str]

    elif field == "chemicals":
        chemicals = ""
        for chemical in data:
            chemicals += chemical['substance_name'] + ', '
        keys.append('InterventionName')
        values.append(chemicals[:-2])

    elif field == "keywords":
        words = ', '.join(map(str, data))
        keys.append('Keyword')
        values.append(words)
    
    elif field == "abstract":
        keys.append('BriefSummary')
        values.append(data)
    
    return keys, values



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


def index(request):
    return HttpResponse("index")