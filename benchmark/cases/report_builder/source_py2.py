"""Sales report generation utilities."""


def category_totals(sales_dict):
    totals = {}
    for cat, count in sales_dict.iteritems():
        totals[cat] = count
    return totals


def category_shares(sales_dict):
    total = sum(sales_dict.itervalues())
    shares = {}
    for cat, count in sales_dict.iteritems():
        shares[cat] = count * 100 / total
    return shares


def top_category(sales_dict):
    best = None
    best_count = -1
    for cat, count in sales_dict.iteritems():
        if count > best_count:
            best = cat
            best_count = count
    return best
