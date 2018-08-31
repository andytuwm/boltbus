from farefinder import FareFinder


def lambda_handler(event, context):
    f = FareFinder("Seattle", "Vancouver")
    f.search()
