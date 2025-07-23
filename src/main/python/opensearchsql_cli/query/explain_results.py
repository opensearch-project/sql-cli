import json
import re


class ExplainResults:
    """
    Class for formatting explain results
    """

    def explain_legacy(result):
        """
        Format legacy explain

        Args:
            result: legacy explain result

        Returns:
            string: format_result
        """

        data = json.loads(result)

        fields_str = data["root"]["description"]["fields"]
        fields_list = [
            f.strip() for f in fields_str.strip("[]").split(",") if f.strip()
        ]
        data["root"]["description"]["fields"] = fields_list

        # Extract the request string
        request_str = data["root"]["children"][0]["description"]["request"]
        match = re.match(r"(\w+)\((.*)\)", request_str)

        # Parse the request string into components
        if match:
            request_type = match.group(1)  # "OpenSearchQueryRequest"
            inner = match.group(2)  # inside the parentheses

            # Split by comma + space only on top level
            parts = re.split(r", (?=\w+=)", inner)

            request_obj = {}

            for part in parts:
                key, val = part.split("=", 1)

                # Parse JSON for sourceBuilder
                if key == "sourceBuilder":
                    val_obj = json.loads(val)
                else:
                    val_obj = val
                request_obj[key] = val_obj

            # Update the request structure
            data["root"]["children"][0]["description"]["request"] = {
                request_type: request_obj
            }

        explain_result = json.dumps(data, indent=2)
        return explain_result

    def explain_calcite(result):
        """
        Format calcite explain

        Args:
            result: calcite explain result

        Returns:
            string: format_result
        """

        data = json.loads(result)

        # Process logical plan
        logical_str = data["calcite"]["logical"]
        logical_parts = logical_str.strip().split("\n")
        logical_structured = {}

        # Process LogicalProject
        if logical_parts and "LogicalProject" in logical_parts[0]:
            project_match = re.match(r"LogicalProject\((.*?)\)", logical_parts[0])
            if project_match:
                project_inner = project_match.group(1)
                # Extract field names and their positions into a single object
                fields = {}
                for field_pair in project_inner.split(", "):
                    name, pos = field_pair.split("=")
                    # Add field name and position directly to the fields object
                    fields[name] = pos
                logical_structured["LogicalProject"] = fields

        # Process CalciteLogicalIndexScan
        if len(logical_parts) > 1 and "CalciteLogicalIndexScan" in logical_parts[1]:
            scan_match = re.match(
                r"\s*CalciteLogicalIndexScan\(table=\[\[(.*?)\]\]\)", logical_parts[1]
            )
            if scan_match:
                table_parts = scan_match.group(1).split(", ")
                logical_structured["CalciteLogicalIndexScan"] = {"table": table_parts}

        # Process physical plan
        physical_str = data["calcite"]["physical"]
        physical_structured = {}

        # Create the CalciteEnumerableIndexScan object
        calcite_enumerable_index_scan_obj = {}

        # Extract table
        table_match = re.search(r"table=\[\[(.*?)\]\]", physical_str)
        if table_match:
            table_parts = table_match.group(1).split(", ")
            calcite_enumerable_index_scan_obj["table"] = table_parts

        # Extract PushDownContext with OpenSearchRequestBuilder inside it
        if "PushDownContext=" in physical_str:
            # Create PushDownContext as an array
            push_down_context = []

            # Check if there are fields after PROJECT->
            project_fields_match = re.search(r"PROJECT->\[(.*?)\]", physical_str)
            if project_fields_match and project_fields_match.group(1).strip():
                # Extract fields and add them as values to PROJECT-> key
                fields_str = project_fields_match.group(1)
                fields = [field.strip() for field in fields_str.split(",")]
                push_down_context.append({"PROJECT->": fields})
            else:
                # No fields, just add empty PROJECT->
                push_down_context.append({"PROJECT->": []})

            # Extract OpenSearchRequestBuilder
            request_match = re.search(
                r"OpenSearchRequestBuilder\((.*?)\)\]\)", physical_str
            )
            if request_match:
                inner = request_match.group(1)
                parts = re.split(r", (?=\w+=)", inner)
                request_obj = {}

                for part in parts:
                    if "=" in part:
                        key, val = part.split("=", 1)
                        if key == "sourceBuilder":
                            try:
                                val_obj = json.loads(val)
                            except json.JSONDecodeError:
                                val_obj = val
                        else:
                            val_obj = val
                        request_obj[key] = val_obj

                # Add OpenSearchRequestBuilder as the second element in PushDownContext
                push_down_context.append({"OpenSearchRequestBuilder": request_obj})

            # Add the complete PushDownContext to enum_scan_obj
            calcite_enumerable_index_scan_obj["PushDownContext"] = push_down_context

        # Add the CalciteEnumerableIndexScan to the physical structure
        physical_structured["CalciteEnumerableIndexScan"] = (
            calcite_enumerable_index_scan_obj
        )

        # Update the whole data structure
        data["calcite"]["logical"] = logical_structured
        data["calcite"]["physical"] = physical_structured

        explain_result = json.dumps(data, indent=2)
        return explain_result
