
import pandas as pd
import json
  
df = pd.DataFrame(pd.read_excel("ncd_indicators_small.xlsx"))
features = []
descriptions = []
ncd_indicators = []
ncd_indicator_object = {}

for idx, row in df.iterrows():
    feature = row['abbreviation']
    description = row['description']
    
    features.append(feature)
    descriptions.append(description)
    

row_dict = {}
json_rows = []
for i in range(0, len(features)):
    row_dict = df.loc[i].to_dict()
    json_rows.append(row_dict)
    
for row in json_rows:
    ncd_indicator_object[row['abbreviation']] = {
        "type": "string",
        "description": row['description']
    }

ncd_indicators_json = json.dumps(ncd_indicator_object)

with open("ncd_indicators.json", "w") as outfile:
    outfile.write(ncd_indicators_json)

if __name__ == '__main__':
    print(ncd_indicators_json)