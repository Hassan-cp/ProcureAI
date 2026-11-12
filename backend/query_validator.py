from copy import deepcopy
import re


# ============================================================
# CONFIGURATION
# ============================================================

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

ALLOWED_STAGES = {
    "$match",
    "$group",
    "$sort",
    "$limit",
    "$project",
    "$count",
}

MAX_STAGES = 10
MAX_RESULTS = 100
MAX_MATCH_VALUES = 100
MAX_REGEX_LENGTH = 100

COMPARISON_OPERATORS = {
    "$eq",
    "$ne",
    "$gt",
    "$gte",
    "$lt",
    "$lte",
    "$in",
    "$nin",
    "$exists",
}

ACCUMULATOR_OPERATORS = {
    "$sum",
    "$avg",
    "$min",
    "$max",
    "$first",
    "$last",
}

EXPRESSION_OPERATORS = {
    "$add",
    "$subtract",
    "$multiply",
    "$divide",
    "$ifNull",
    "$cond",
    "$year",
    "$month",
}


# ============================================================
# HELPERS
# ============================================================

def require_object(value, label):
    if not isinstance(value, dict) or not value:
        raise ValueError(
            f"{label} must be a non-empty object."
        )


def validate_field_name(name, available_fields):
    if not isinstance(name, str) or name not in available_fields:
        raise ValueError(
            f"Unknown MongoDB field: {name}"
        )


def validate_output_name(name):
    if (
        not isinstance(name, str)
        or not name
        or name.startswith("$")
        or "." in name
        or "\x00" in name
    ):
        raise ValueError(
            f"Invalid output field name: {name}"
        )


def validate_literal(value):
    """
    Allow simple JSON values and bounded arrays.
    """

    if value is None or isinstance(
        value, (str, bool, int, float)
    ):
        return

    if isinstance(value, list):
        if len(value) > MAX_MATCH_VALUES:
            raise ValueError(
                "Too many values in array."
            )

        for item in value:
            validate_literal(item)

        return

    raise ValueError(
        "Unsupported literal value."
    )


# ============================================================
# SAFE REGEX VALIDATION
# ============================================================

def validate_safe_regex(pattern):
    """
    Allow simple literal text searches only.

    Examples accepted:
        toner
        laptop
        office supplies

    Examples rejected:
        .*
        (a+)+
        ^toner
        toner|printer
    """

    if not isinstance(pattern, str):
        raise ValueError(
            "$regex requires a string."
        )

    if not 1 <= len(pattern) <= MAX_REGEX_LENGTH:
        raise ValueError(
            "Invalid regex length."
        )

    # Reject regex metacharacters.
    # Only ordinary literal text searches are permitted.
    if re.search(r"[\\.^$*+?{}\[\]|()]", pattern):
        raise ValueError(
            "Regex special characters are not allowed."
        )

    # Reject control characters.
    if any(ord(char) < 32 for char in pattern):
        raise ValueError(
            "Control characters are not allowed in regex."
        )


# ============================================================
# EXPRESSIONS
# ============================================================

def validate_expression(value, available_fields, depth=0):

    if depth > 10:
        raise ValueError(
            "Expression is too deeply nested."
        )

    if isinstance(value, str):

        if value.startswith("$$"):
            raise ValueError(
                "MongoDB variables are not supported."
            )

        if value.startswith("$"):
            validate_field_name(
                value[1:],
                available_fields
            )

        return

    if value is None or isinstance(
        value, (bool, int, float)
    ):
        return

    if isinstance(value, list):

        if len(value) > MAX_MATCH_VALUES:
            raise ValueError(
                "Expression array is too large."
            )

        for item in value:
            validate_expression(
                item,
                available_fields,
                depth + 1
            )

        return

    if isinstance(value, dict):

        require_object(value, "Expression")

        if len(value) != 1:
            raise ValueError(
                "Expression must contain one operator."
            )

        operator, argument = next(
            iter(value.items())
        )

        if operator not in EXPRESSION_OPERATORS:
            raise ValueError(
                f"Expression operator not allowed: {operator}"
            )

        if operator in {"$year", "$month"}:

            validate_expression(
                argument,
                available_fields,
                depth + 1
            )

        elif operator == "$cond":

            if (
                not isinstance(argument, list)
                or len(argument) != 3
            ):
                raise ValueError(
                    "$cond requires three arguments."
                )

            for item in argument:
                validate_expression(
                    item,
                    available_fields,
                    depth + 1
                )

        else:

            if (
                not isinstance(argument, list)
                or len(argument) < 2
            ):
                raise ValueError(
                    f"{operator} requires an argument array."
                )

            if operator in {
                "$subtract",
                "$divide",
                "$ifNull"
            }:
                if len(argument) != 2:
                    raise ValueError(
                        f"{operator} requires exactly two arguments."
                    )

            for item in argument:
                validate_expression(
                    item,
                    available_fields,
                    depth + 1
                )

        return

    raise ValueError(
        "Unsupported expression value."
    )


# ============================================================
# $MATCH
# ============================================================

def validate_match(content, available_fields, depth=0):

    if depth > 10:
        raise ValueError(
            "$match is too deeply nested."
        )

    require_object(content, "$match")

    for field, condition in content.items():

        # ----------------------------------------
        # Logical operators
        # ----------------------------------------

        if field in {"$and", "$or"}:

            if (
                not isinstance(condition, list)
                or not 1 <= len(condition) <= MAX_MATCH_VALUES
            ):
                raise ValueError(
                    f"{field} requires a non-empty array."
                )

            for subcondition in condition:
                validate_match(
                    subcondition,
                    available_fields,
                    depth + 1
                )

            continue

        # ----------------------------------------
        # Validate field
        # ----------------------------------------

        validate_field_name(
            field,
            available_fields
        )

        if isinstance(condition, dict):

            require_object(
                condition,
                "Match condition"
            )

            # ------------------------------------
            # Safe regex handling
            # ------------------------------------

            if "$regex" in condition:

                # Only regex and options are permitted
                # together in a regex condition.
                if not set(condition).issubset(
                    {"$regex", "$options"}
                ):
                    raise ValueError(
                        "Cannot combine regex with other operators."
                    )

                validate_safe_regex(
                    condition["$regex"]
                )

                if "$options" in condition:
                    if condition["$options"] != "i":
                        raise ValueError(
                            "Only case-insensitive regex is allowed."
                        )

                continue

            # $options cannot appear alone.
            if "$options" in condition:
                raise ValueError(
                    "$options requires $regex."
                )

            # ------------------------------------
            # Standard comparison operators
            # ------------------------------------

            for operator, value in condition.items():

                if operator not in COMPARISON_OPERATORS:
                    raise ValueError(
                        f"Match operator not allowed: {operator}"
                    )

                if operator in {"$in", "$nin"}:

                    if not isinstance(value, list):
                        raise ValueError(
                            f"{operator} requires an array."
                        )

                    if len(value) > MAX_MATCH_VALUES:
                        raise ValueError(
                            "Match array is too large."
                        )

                    for item in value:

                        if isinstance(item, (list, dict)):
                            raise ValueError(
                                "Nested match values are not supported."
                            )

                        validate_literal(item)

                elif operator == "$exists":

                    if type(value) is not bool:
                        raise ValueError(
                            "$exists requires true or false."
                        )

                else:

                    if isinstance(value, (dict, list)):
                        raise ValueError(
                            "Nested comparison values are not supported."
                        )

                    validate_literal(value)

        else:
            validate_literal(condition)


# ============================================================
# $GROUP
# ============================================================

def validate_group(content, available_fields):

    require_object(content, "$group")

    if "_id" not in content:
        raise ValueError(
            "$group requires _id."
        )

    group_id = content["_id"]

    if isinstance(group_id, dict):

        require_object(
            group_id,
            "$group _id"
        )

        for key, expression in group_id.items():

            validate_output_name(key)

            validate_expression(
                expression,
                available_fields
            )

    else:

        validate_expression(
            group_id,
            available_fields
        )

    new_fields = {"_id"}

    for field, expression in content.items():

        if field == "_id":
            continue

        validate_output_name(field)

        require_object(
            expression,
            "Accumulator"
        )

        if len(expression) != 1:
            raise ValueError(
                "Accumulator must contain exactly one operator."
            )

        operator, argument = next(
            iter(expression.items())
        )

        if operator not in ACCUMULATOR_OPERATORS:
            raise ValueError(
                f"Accumulator not allowed: {operator}"
            )

        validate_expression(
            argument,
            available_fields
        )

        new_fields.add(field)

    return new_fields


# ============================================================
# $SORT
# ============================================================

def validate_sort(content, available_fields):

    require_object(content, "$sort")

    for field, direction in content.items():

        validate_field_name(
            field,
            available_fields
        )

        if (
            type(direction) is not int
            or direction not in (1, -1)
        ):
            raise ValueError(
                f"Invalid sort direction for {field}"
            )


# ============================================================
# $PROJECT
# ============================================================

def validate_project(content, available_fields):

    require_object(content, "$project")

    inclusion = False
    exclusion = False
    new_fields = set()

    for field, expression in content.items():

        validate_output_name(field)

        if expression == 0 and type(expression) is int:

            if field != "_id":
                exclusion = True

        elif expression == 1 and type(expression) is int:

            inclusion = True

            validate_field_name(
                field,
                available_fields
            )

            new_fields.add(field)

        else:

            inclusion = True

            validate_expression(
                expression,
                available_fields
            )

            new_fields.add(field)

    if inclusion and exclusion:
        raise ValueError(
            "Cannot mix inclusion and exclusion in $project."
        )

    if exclusion:

        return available_fields - {
            field
            for field, expression in content.items()
            if type(expression) is int and expression == 0
        }

    if "_id" in available_fields and content.get("_id") != 0:
        new_fields.add("_id")

    return new_fields


# ============================================================
# $COUNT
# ============================================================

def validate_count(content):

    validate_output_name(content)

    if content == "_id":
        raise ValueError(
            "$count cannot use _id."
        )

    return {content}


# ============================================================
# MAIN VALIDATOR
# ============================================================

def validate_pipeline(pipeline):

    if not isinstance(pipeline, list):
        raise ValueError(
            "Pipeline must be a list."
        )

    if not 1 <= len(pipeline) <= MAX_STAGES:
        raise ValueError(
            "Invalid number of pipeline stages."
        )

    safe_pipeline = deepcopy(pipeline)

    available_fields = set(ALLOWED_FIELDS)

    for index, stage in enumerate(safe_pipeline):

        if (
            not isinstance(stage, dict)
            or len(stage) != 1
        ):
            raise ValueError(
                "Each stage must contain exactly one operator."
            )

        operator, content = next(
            iter(stage.items())
        )

        if operator not in ALLOWED_STAGES:
            raise ValueError(
                f"MongoDB stage not allowed: {operator}"
            )

        if operator == "$match":

            validate_match(
                content,
                available_fields
            )

        elif operator == "$group":

            available_fields = validate_group(
                content,
                available_fields
            )

        elif operator == "$sort":

            validate_sort(
                content,
                available_fields
            )

        elif operator == "$project":

            available_fields = validate_project(
                content,
                available_fields
            )

        elif operator == "$count":

            available_fields = validate_count(
                content
            )

            if index != len(safe_pipeline) - 1:
                raise ValueError(
                    "$count must be the final stage."
                )

        elif operator == "$limit":

            if (
                type(content) is not int
                or not 1 <= content <= MAX_RESULTS
            ):
                raise ValueError(
                    "Invalid result limit."
                )

    # Always cap final output.
    safe_pipeline.append({
        "$limit": MAX_RESULTS
    })

    return safe_pipeline


# ============================================================
# VALIDATOR TESTS
# ============================================================

if __name__ == "__main__":

    def run_test(name, pipeline, should_pass):

        try:
            validate_pipeline(pipeline)

            if should_pass:
                print(f"PASSED: {name}")
                return True

            print(f"FAILED: {name} was accepted!")
            return False

        except ValueError as error:

            if should_pass:
                print(f"FAILED: {name} -> {error}")
                return False

            print(f"BLOCKED: {name} -> {error}")
            return True

    tests = [
        (
            "Valid supplier spending query",
            [
                {
                    "$group": {
                        "_id": "$Supplier Name",
                        "totalSpending": {
                            "$sum": "$Total Price"
                        }
                    }
                },
                {"$sort": {"totalSpending": -1}},
                {"$limit": 5}
            ],
            True
        ),
        (
            "Valid toner search",
            [
                {
                    "$match": {
                        "Item Name": {
                            "$regex": "toner",
                            "$options": "i"
                        }
                    }
                },
                {"$limit": 5}
            ],
            True
        ),
        (
            "Valid item description search",
            [
                {
                    "$match": {
                        "Item Description": {
                            "$regex": "office supplies",
                            "$options": "i"
                        }
                    }
                },
                {"$limit": 5}
            ],
            True
        ),
        (
            "Unsafe regex wildcard",
            [
                {
                    "$match": {
                        "Item Name": {
                            "$regex": ".*",
                            "$options": "i"
                        }
                    }
                }
            ],
            False
        ),
        (
            "Unsafe regex nested repetition",
            [
                {
                    "$match": {
                        "Item Name": {
                            "$regex": "(a+)+"
                        }
                    }
                }
            ],
            False
        ),
        (
            "Unsafe regex options",
            [
                {
                    "$match": {
                        "Item Name": {
                            "$regex": "toner",
                            "$options": "im"
                        }
                    }
                }
            ],
            False
        ),
        (
            "Regex options without regex",
            [
                {
                    "$match": {
                        "Item Name": {
                            "$options": "i"
                        }
                    }
                }
            ],
            False
        ),
        (
            "Unsafe $out stage",
            [
                {"$out": "another_collection"}
            ],
            False
        ),
        (
            "Unsafe $merge stage",
            [
                {"$merge": "another_collection"}
            ],
            False
        ),
        (
            "Unsafe $lookup stage",
            [
                {"$lookup": {"from": "users"}}
            ],
            False
        ),
        (
            "Unsafe $function operator",
            [
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
            ],
            False
        ),
        (
            "Invalid group field",
            [
                {
                    "$group": {
                        "_id": "$SupplierName",
                        "totalSpending": {
                            "$sum": "$Total Price"
                        }
                    }
                }
            ],
            False
        ),
        (
            "Invalid sort field",
            [
                {"$sort": {"wrongField": -1}}
            ],
            False
        ),
        (
            "Invalid sort direction",
            [
                {"$sort": {"Total Price": 5}}
            ],
            False
        ),
        (
            "Valid match",
            [
                {
                    "$match": {
                        "Department Name": "Transportation"
                    }
                },
                {"$limit": 10}
            ],
            True
        ),
        (
            "Invalid match field",
            [
                {
                    "$match": {
                        "Wrong Department": "Transportation"
                    }
                }
            ],
            False
        ),
        (
            "Valid count",
            [
                {"$count": "totalPurchases"}
            ],
            True
        ),
        (
            "Invalid count placement",
            [
                {"$count": "totalPurchases"},
                {"$sort": {"totalPurchases": -1}}
            ],
            False
        ),
        (
            "Valid project",
            [
                {
                    "$project": {
                        "Supplier Name": 1,
                        "Total Price": 1,
                        "_id": 0
                    }
                }
            ],
            True
        ),
        (
            "Invalid project field",
            [
                {
                    "$project": {
                        "SupplierName": 1
                    }
                }
            ],
            False
        ),
    ]

    passed = 0

    for name, pipeline, should_pass in tests:

        if run_test(name, pipeline, should_pass):
            passed += 1

    print("\n" + "=" * 55)
    print("VALIDATOR TEST SUMMARY")
    print("=" * 55)
    print(f"Passed: {passed}/{len(tests)}")
    print(f"Failed: {len(tests) - passed}/{len(tests)}")
