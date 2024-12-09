
import pandas as pd
import json
  
df = pd.DataFrame(pd.read_excel("ncd_indicators.xlsx"))
ncd_indicators = []
ncd_indicator_object = {}

for idx, row in df.iterrows():
    feature = row['VariableName']
    description = row['Description']
    ncd_indicator_object[feature] = {
        "type": "string",
        "description": description
    }
    ncd_indicators.append(ncd_indicator_object)
    
ncd_indicators_json = json.dumps(ncd_indicators)

with open("ncd_indicators.json", "w") as outfile:
    outfile.write(ncd_indicators_json)


if __name__ == '__main__':
    print(ncd_indicators_json)