import requests, json
import pandas as pd

lens_key = 'JsGWcp0DKnphJq3dA71k7hkS4BVKG8ZC0AGYtWtbZB5slK1D8UTH'
lens_size = 100

# LENS PATENT
def get_lens_p_df(entries):
    if len(entries) == 0:
        return pd.DataFrame()

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
            row['Title'] = title['text']
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
                row[field_dict[f].title()] = ls_str
            except KeyError:
                row[field_dict[f].title()] = ""

    for string in ['ipcr', 'cpc']:
        try:
            section = bib['classifications_' + string]
            section_ls = []
            for c in section['classifications']:
                section_ls.append(c['symbol'])
            section_str = ', '.join(section_ls)
            row[string.upper()] = section_str
        except KeyError:
            row[string.upper()] = ""

    try:
        full_list = result['claims']
        for entry in full_list:
            if entry['lang'] == 'en':
                all_claims = entry['claims']
                full_text = ""
                for claim in all_claims:
                    claim_text = claim['claim_text'][0]
                    # if "(canceled)" in claim_text:
                    #     continue
                    full_text += claim_text + " "
                row['Claims'] = full_text
    except KeyError:
        row['Claims'] = ""

    return row