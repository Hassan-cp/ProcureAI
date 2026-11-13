"""Conservative, fully matched plans for common procurement metrics.

No result cache: every request reads current data. Unrecognized qualifiers
must fall through to the model rather than silently dropping constraints.
"""
import re
from datetime import datetime, timedelta, timezone


def common_query(question):
    text = ' '.join(question.lower().strip().rstrip('?.!').split())
    bounded = re.fullmatch(
        r'(?:what is |what was |show me |give me )?(?:the )?'
        r'(?:most recent|latest|last) purchase (date|year) '
        r'(in|before|after|on or before|on or after|since) ([0-9]{4}(?:-[0-9]{2}-[0-9]{2})?)', text)
    if bounded:
        unit, relation, literal = bounded.groups()
        try:
            is_year = len(literal) == 4
            start = datetime(int(literal), 1, 1, tzinfo=timezone.utc) if is_year else datetime.strptime(literal, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            end = datetime(start.year+1,1,1,tzinfo=timezone.utc) if is_year else start+timedelta(days=1)
        except (ValueError, OverflowError):
            return None
        def stamp(value):
            return {'$date': value.isoformat().replace('+00:00', 'Z')}
        # "Before" excludes the whole named day/year; "after" excludes it too.
        bounds = {
            'in': {'$gte':stamp(start),'$lt':stamp(end)},
            'before': {'$lt':stamp(start)},
            'after': {'$gte':stamp(end)},
            'on or before': {'$lt':stamp(end)},
            'on or after': {'$gte':stamp(start)},
            'since': {'$gte':stamp(start)},
        }[relation]
        return {'pipeline':[{'$match':{'Purchase Date':bounds}}, {'$group':{
            '_id':None, 'latestYear' if unit=='year' else 'latestDate':{
                '$max':{'$year':'$Purchase Date'} if unit=='year' else '$Purchase Date'
            }
        }}]}
    if re.fullmatch(r'how many purchases (?:are in the database|are there in the database)', text):
        return {'pipeline': [{'$count': 'count'}]}
    match = re.fullmatch(r'how many purchases were made in ([0-9]{4})', text)
    if match:
        year = int(match.group(1))
        if 1 <= year < 9999:
            return {'pipeline': [{'$match': {'Purchase Date': {
                '$gte': {'$date': f'{year:04d}-01-01T00:00:00Z'},
                '$lt': {'$date': f'{year+1:04d}-01-01T00:00:00Z'},
            }}}, {'$count': 'count'}]}
    if re.fullmatch(r'what is the total spending (?:across all purchases|for all purchases)', text):
        return {'pipeline': [{'$group': {'_id': None, 'totalSpending': {'$sum': '$Total Price'}}}]}
    match = re.fullmatch(r'(?:who are|which are) the top ([1-9]|[1-9][0-9]|100) (suppliers|departments) by total spending', text)
    if match:
        field = 'Supplier Name' if match.group(2) == 'suppliers' else 'Department Name'
        return {'pipeline': [{'$group': {'_id': '$'+field, 'totalSpending': {'$sum': '$Total Price'}}},
                             {'$sort': {'totalSpending': -1, '_id': 1}}, {'$limit': int(match.group(1))}]}
    return None


def escape_text(value):
    return re.sub(r'([\\`*_{}\[\]()<>#|])', r'\\\1', str(value)).replace('\n', ' ')


def aggregate_answer(pipeline, results):
    """Render only known scalar/ranking shapes, using actual result field names.

    Unknown projections, transformations, or extra stages fall through. This
    avoids interpreting arbitrary results as a metric the query did not compute.
    """
    if not results:
        return None
    stages = [s for s in pipeline if '$match' not in s]
    if len(stages) == 1 and '$count' in stages[0]:
        key = stages[0]['$count']
        if len(results) == 1 and set(results[0]) == {key}:
            return f"Matching purchases: {results[0][key]:,}."
    if not stages or '$group' not in stages[0]:
        return None
    group = stages[0]['$group']
    metrics = [k for k in group if k != '_id']
    if len(metrics) != 1:
        return None
    key = metrics[0]
    expr = group[key]
    if any(set(s) - {'$sort', '$limit'} for s in stages[1:]):
        return None
    if group['_id'] is None and len(results) == 1 and set(results[0]) <= {'_id', key} and key in results[0]:
        value = results[0][key]
        if value is None:
            return 'No matching procurement records were found.'
        if expr == {'$sum': '$Total Price'} and isinstance(value, (int, float)):
            return f'The total spending for the requested purchases is ${value:,.2f}.'
        if expr == {'$sum': 1} and isinstance(value, int):
            return f'Matching purchases: {value:,}.'
        if expr == {'$max': '$Purchase Date'} and isinstance(value, datetime):
            return f'The most recent purchase date for the requested purchases is {value:%B} {value.day}, {value.year}.'
        if expr == {'$max': {'$year': '$Purchase Date'}} and isinstance(value, int):
            return f'The most recent purchase year for the requested purchases is {value}.'
    if group['_id'] in ('$Supplier Name', '$Department Name') and expr == {'$sum': '$Total Price'}:
        # Do not call an ascending or unsorted result a "top" ranking.
        sorts = [s['$sort'] for s in stages[1:] if '$sort' in s]
        if len(sorts) != 1 or next(iter(sorts[0].items())) != (key, -1):
            return None
        if any(set(row) - {'_id', key} or key not in row or '_id' not in row or not isinstance(row[key], (int,float)) for row in results):
            return None
        label = 'suppliers' if group['_id'] == '$Supplier Name' else 'departments'
        rows = [f"{i}. **{escape_text(row['_id'])}**: ${row[key]:,.2f}" for i,row in enumerate(results,1)]
        return f'The top {len(rows)} {label} by total spending for the requested purchases are:\n\n' + '\n'.join(rows)
    return None
