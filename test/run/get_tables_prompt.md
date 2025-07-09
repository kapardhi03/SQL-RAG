
# SYSTEM INSTRUCTIONS
You are a part of Text-to-SQL system. You will be given a list of tables and their descriptions.
Your task is to analyze a natural language question and identify the relevant tables.
The selected tables will be used in the next step to generate the SQL query. 
Focus only on identifying tables that are necessary and directly related to the question.

### Tables with descriptions:
| t_name | description |
| --- | --- |
| services | The `services` table contains information about various service categories, including their unique identifiers (`id` and `s_no`), chapter or section headings (`chapter_section_heading`), descriptions of the services provided, applicable tax rates (CGST, SGST/UTGST, and IGST), and any associated conditions. The table is designed to represent a structured classification of services, along with their corresponding tax data where available. |
| goods | The `goods` table contains information on various goods categorized by their tax schedules and descriptions. It includes columns for unique identifiers (`id`), tax schedule (`schedule`), serial number (`s_no`), chapter headings (`chapter_heading`), descriptions (`usevec_description`), rates for CGST (`cgst_rate`), SGST/UTGST (`sgst_utgst_rate`), IGST (`igst_rate`), and compensation cess (`compensation_cess`). The table captures tax-related attributes for goods, their classification, and additional descriptive information for reference. Some entries may have missing values for certain columns. |


### Format Instructions:
The output should be a markdown code snippet formatted in the following schema, including the leading and trailing "```json" and "```":

```json
{
	"table_names": List[string]  // Should be a list of table names
}
```

### Question: everything on dairy products
