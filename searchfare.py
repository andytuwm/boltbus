import argparse

from farefinder import FareFinder, Time

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--start', help='the starting location (ex. Vancouver)', required=True)
    parser.add_argument('-e', '--end', help='the ending location (ex. Seattle)', required=True)
    parser.add_argument('-w', '--weeks', help='the number of weeks in advance to search for fares from')
    parser.add_argument('-p', '--price', help='the desired maximum acceptable price of a fare')
    parser.add_argument('-pm', '--morning', action='store_true', help='search for fares in the morning')
    parser.add_argument('-pn', '--noon', action='store_true', help='search for fares around noon')
    parser.add_argument('-pe', '--evening', action='store_true', help='search for fares in the evening')
    parser.add_argument('-na', '--no_alert', action='store_false', help="if this flag is set, don't send email alerts.")

    args = parser.parse_args()

    flags = {}
    if args.weeks:
        flags["search_after_week"] = int(args.weeks)
    if args.price:
        flags["max_price"] = float(args.price)
    if args.morning:
        flags["preferred_time"] = Time.MORNING
    elif args.noon:
        flags["preferred_time"] = Time.NOON
    elif args.evening:
        flags["preferred_time"] = Time.AFTERNOON

    f = FareFinder(args.start, args.end, email_alert=args.no_alert, **flags)
    f.search()
