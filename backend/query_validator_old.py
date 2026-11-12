from copy import deepcopy

ALLOWED_STAGES = {
    "$match",
    "$group",
    "$sort",
    "$limit",
    "$project",
    "$count",
}

ALLOWED_OPERATORS = {
    "$eq",
    "$ne",
    "$gt",
    "$gte",
    "$lt",
    "$lte",
    "$in",
    "$nin",
    "$and",
    "$or",
    "$not",
    "$exists",
    "$sum",
    "$avg",
    "$min",
    "$max",
    "$first",
    "$last",
    "$add",
    "$subtract",
    "$multiply",
    "$divide",
    "$ifNull",
    "$cond",
    "$year",
    "$month",
}
ALLOWED_FIELDS = {
    "Creation Date",
    "Purchase Date",
    "Fiscal Year",
    "LPA Number",
    "Purchase Order Number",
    "Requisition Number",
    "Acquisition Type",
    "Sub-Acquisition Type",
    "Acquisition Method",
    "Sub-Acquisition Method",
    "Department Name",
    "Supplier Code",
    "Supplier Name",
    "Supplier Qualifications",
    "Supplier Zip Code",
    "CalCard",
    "Item Name",
    "Item Description",
    "Quantity",
    "Unit Price",
    "Total Price",
    "Classification Codes",
    "Normalized UNSPSC",
    "Commodity Title",
    "Class",
    "Class Title",
    "Family",
    "Family Title",
    "Segment",
    "Segment Title",
    "Location",
}

MAX_STAGES = 10
MAX_RESULTS = 100


def check_operators(value):
    """Check operators recursively, including nested dictionaries and lists."""

    if isinstance(value, dict):
        for key, nested_value in value.items():

            if not isinstance(key, str):
                raise ValueError("MongoDB keys must be strings.")

            if key.startswith("$") and key not in ALLOWED_OPERATORS:
                raise ValueError(f"MongoDB operator not allowed: {key}")

            check_operators(nested_value)

    elif isinstance(value, list):
        for item in value:
            check_operators(item)


def check_field_references(value):
    """Check references to original MongoDB fields."""

    if isinstance(value, dict):
        for key, nested_value in value.items():
            check_field_references(nested_value)

    elif isinstance(value, list):
        for item in value:
            check_field_references(item)

    elif isinstance(value, str):
        if value.startswith("$") and not value.startswith("$$"):
            field_name = value[1:]

            if field_name not in ALLOWED_FIELDS:
                raise ValueError(
                    f"Unknown MongoDB field: {field_name}"
                )

def validate_group_fields(group_content, available_fields):
    """Validate field references inside $group."""

    if not isinstance(group_content, dict):
        raise ValueError("$group must contain an object.")

    if "_id" not in group_content:
        raise ValueError("$group requires _id.")

    def check_reference(value):
        if isinstance(value, str) and value.startswith("$"):
            field_name = value[1:]

            if field_name not in available_fields:
                raise ValueError(
                    f"Unknown MongoDB field: {field_name}"
                )

        elif isinstance(value, dict):
            for nested_value in value.values():
                check_reference(nested_value)

        elif isinstance(value, list):
            for item in value:
                check_reference(item)

    check_reference(group_content["_id"])

    new_fields = {"_id"}

    for field_name, expression in group_content.items():
        if field_name == "_id":
            continue

        if not isinstance(field_name, str):
            raise ValueError("Calculated field name must be a string.")

        if field_name.startswith("$") or "." in field_name:
            raise ValueError("Invalid calculated field name.")

        check_reference(expression)
        new_fields.add(field_name)

    return new_fields

def validate_sort_fields(sort_content, available_fields):
    """Validate field names and directions inside $sort."""

    if not isinstance(sort_content, dict) or not sort_content:
        raise ValueError("$sort must contain a non-empty object.")

    for field_name, direction in sort_content.items():

        if not isinstance(field_name, str):
            raise ValueError("$sort field name must be a string.")

        if field_name not in available_fields:
            raise ValueError(
                f"Unknown MongoDB sort field: {field_name}"
            )

        if type(direction) is not int or direction not in (1, -1):
            raise ValueError(
                f"Invalid sort direction for {field_name}"
            )

            
def validate_pipeline(pipeline):
    if not isinstance(pipeline, list):
        raise ValueError("Pipeline must be a list.")

    if not 1 <= len(pipeline) <= MAX_STAGES:
        raise ValueError("Invalid number of pipeline stages.")

    # Do not modify the original pipeline
    safe_pipeline = deepcopy(pipeline)

    # Fields available at the beginning
    available_fields = set(ALLOWED_FIELDS)

    for stage in safe_pipeline:
        if not isinstance(stage, dict) or len(stage) != 1:
            raise ValueError("Each stage must contain one operator.")

        operator, stage_content = next(iter(stage.items()))

        if operator not in ALLOWED_STAGES:
            raise ValueError(
                f"MongoDB stage not allowed: {operator}"
            )

        # Validate operators inside the stage
        check_operators(stage_content)

        # Validate fields used by $group
        if operator == "$group":
            available_fields = validate_group_fields(
                stage_content,
                available_fields
            )

        # Validate fields and directions used by $sort
        if operator == "$sort":
            validate_sort_fields(
                stage_content,
                available_fields
            )

    limits = [
        stage["$limit"]
        for stage in safe_pipeline
        if "$limit" in stage
    ]

    for limit in limits:
        if type(limit) is not int or not 1 <= limit <= MAX_RESULTS:
            raise ValueError("Invalid result limit.")

    # Always cap final output
    safe_pipeline.append({"$limit": MAX_RESULTS})

    return safe_pipeline

if __name__ == "__main__":

    safe_pipeline = [
        {
            "$group": {
                "_id": "$Supplier Name",
                "totalSpending": {"$sum": "$Total Price"}
            }
        },
        {"$sort": {"totalSpending": -1}},
        {"$limit": 5},
    ]

    print("TEST 1: Safe query")
    try:
        result = validate_pipeline(safe_pipeline)
        print("PASSED:", result)
    except ValueError as error:
        print("FAILED:", error)

    unsafe_pipeline = [
        {"$out": "another_collection"}
    ]

    print("\nTEST 2: Unsafe stage")
    try:
        validate_pipeline(unsafe_pipeline)
        print("FAILED: Unsafe stage was accepted!")
    except ValueError as error:
        print("BLOCKED:", error)

    nested_unsafe_pipeline = [
        {
            "$project": {
                "dangerous": {
                    "$function": {
                        "body": "function() { return 1; }",
                        "args": [],
                        "lang": "js"
                    }
                }
            }
        }
    ]

    print("\nTEST 3: Unsafe nested operator")
    try:
        validate_pipeline(nested_unsafe_pipeline)
        print("FAILED: Unsafe operator was accepted!")
    except ValueError as error:
        print("BLOCKED:", error)

    print("\nTEST 4: Valid field reference")

    try:
        check_field_references("$Supplier Name")
        print("PASSED: Valid field accepted")
    except ValueError as error:
        print("FAILED:", error)

    print("\nTEST 5: Invalid field reference")

    try:
        check_field_references("$SupplierName")
        print("FAILED: Invalid field was accepted!")
    except ValueError as error:
        print("BLOCKED:", error)

    print("\nTEST 6: Calculated field in aggregation")

    calculated_pipeline = [
        {
            "$group": {
                "_id": "$Supplier Name",
                "totalSpending": {"$sum": "$Total Price"}
            }
        },
        {"$sort": {"totalSpending": -1}},
        {"$limit": 5}
    ]

    try:
        result = validate_pipeline(calculated_pipeline)
        print("PASSED: Calculated field pipeline accepted")
    except ValueError as error:
        print("FAILED:", error)

    print("\nTEST 7: Invalid field inside $group")

    invalid_group_pipeline = [
        {
            "$group": {
                "_id": "$SupplierName",
                "totalSpending": {"$sum": "$Total Price"}
            }
        },
        {"$limit": 5}
    ]

    try:
        validate_pipeline(invalid_group_pipeline)
        print("FAILED: Invalid field was accepted!")
    except ValueError as error:
        print("BLOCKED:", error)