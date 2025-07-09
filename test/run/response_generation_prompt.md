# Task: Response generation from Table
You are the last state of a text-to-SQL system. You have to generate a response based on the user query, generated query results. 
Do not use any information other than the user query and the generated query results.

### SQL query results:
| cgst_rate | sgst_utgst_rate | igst_rate | usevec_description |
| --- | --- | --- | --- |
| 0.75 | 0.75 | 1.5 | (i) Construction of affordable residential apartments by a promoter in a Residential Real Estate Project (herein after referred to as RREP) which commences on or after 1 st April, 2019 or in an ongoing RREP in respect of which the promoter has not exercised option to pay integrated tax on construction of apartments at the rates as specified for item (ie) or (if) below, as the case may be, in the manner prescribed therein, intended for sale to a buyer, wholly or partly, except where the entire consideration has been received after issuance of completion certificate, where required, by the competent authority or after its first occupation, whichever is earlier. (Provisions of paragraph 2 of this notification shall apply for valuation of this service) |
| 0.75 | 0.75 | 1.5 | (ic) Construction of affordable residential apartments by a promoter in a Real Estate Project (herein after referred to as REP) other than RREP, which commences on or after 1 st April, 2019 or in an ongoing REP other than RREP in respect of which the promoter has not exercised option to pay integrated tax on construction of apartments at the rates as specified for item (ie) or (if) below, as the case may be, in the manner prescribed therein, intended for sale to a buyer, wholly or partly, except where the entire consideration has been received after issuance of completion certificate, where required, by the competent authority or after its first occupation, whichever is earlier. (Provisions of paragraph 2 of this notification shall apply for valuation of this service) |


### Question: What tax rate applies to building low-income housing?