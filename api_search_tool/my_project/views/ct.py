import requests, json
import pandas as pd
from pandas import json_normalize

state_to_abbrev = {'Alabama': 'AL', 'Alaska': 'AK', 'American Samoa': 'AS', 'Arizona': 'AZ', 'Arkansas': 'AR', 'California': 'CA', 'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE', 'District of Columbia': 'DC', 'Florida': 'FL', 'Georgia': 'GA', 'Guam': 'GU', 'Hawaii': 'HI', 'Idaho': 'ID', 'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA', 'Kansas': 'KS', 'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME', 'Maryland': 'MD', 'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN', 'Mississippi': 'MS', 'Missouri': 'MO', 'Montana': 'MT', 'Nebraska': 'NE', 'Nevada': 'NV', 'New Hampshire': 'NH', 'New Jersey': 'NJ', 'New Mexico': 'NM', 'New York': 'NY', 'North Carolina': 'NC', 'North Dakota': 'ND', 'Northern Mariana Islands': 'MP', 'Ohio': 'OH', 'Oklahoma': 'OK', 'Oregon': 'OR', 'Pennsylvania': 'PA', 'Puerto Rico': 'PR', 'Rhode Island': 'RI', 'South Carolina': 'SC', 'South Dakota': 'SD', 'Tennessee': 'TN', 'Texas': 'TX', 'Utah': 'UT', 'Vermont': 'VT', 'Virgin Islands': 'VI', 'Virginia': 'VA', 'Washington': 'WA', 'West Virginia': 'WV', 'Wisconsin': 'WI', 'Wyoming': 'WY'}

# CLINCICAL TRIALS
def get_ct_df(entries):
    field_names = [
        "NCTId", "OfficialTitle", "LeadSponsorName", "OverallOfficialAffiliation", "OverallOfficialName", 
        "OverallOfficialRole", "InterventionName", "LocationCity", "LocationState", "Keyword", "BriefSummary"]
    cols = [
        "NCTId", "Title", "Sponsor", "Institution", "Authors", 
        "Role", "InterventionName", "Location", "State", "Keyword", "BriefSummary"]

    try:
        del entries['lens_id']
    except KeyError:
        pass

    if len(entries) == 0:
        return pd.DataFrame()

    response_json = make_ct_request(entries, field_names)
    ct_df = ct_json_to_df(response_json, field_names, cols)
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

def ct_json_to_df(response_json, field_names, cols):
    '''Put response data into a dataframe.

    arguments:
    response -- json response from API
    field_names -- global variable that defines the columns

    '''
    try:
        ct_df = json_normalize(response_json['StudyFieldsResponse']['StudyFields'])
    except:
        return pd.DataFrame()

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

    ct_df = ct_df.rename(columns=rename_dict)

    for index, row in ct_df.iterrows():
        cities = row['Location'].split(',')
        states = row['State'].split(',')
        number = len(cities)
        if number < 20:
            new_cities = [c.strip() for c in cities]
            new_states = []
            for state in states:
                state = state.strip()
                try:
                    new_states.append(state_to_abbrev[state])
                except:
                    new_states.append(state)
            locs = [f'{c}, {s}' for c, s in zip(new_cities, new_states)]
            locs = list(set(locs))
            loc_str = '; '.join(locs)
        else:
            loc_str = '20+ locations'

        ct_df.at[index, 'Location'] = loc_str

    ct_df = ct_df.drop(['Rank'], axis=1)
    ct_df = ct_df.drop(['State'], axis=1)

    return ct_df