from utils.cli import *

cli = CLI(
    prime="198766463529478683931867765928436695041",
    r="141515903391459779531506841503331516415",
    r_inv="133854242216446749056083838363708373830",
    providers=[
        Provider(base_url="http://apollo.bocse.carbynestack.io/"),
        Provider(base_url="http://starbuck.bocse.carbynestack.io/")
    ])

secret_id = cli.create_secret(tags={"message":"howdy", "type":"magic"}, values=[5, 15, 25]);
print(secret_id)
print(cli.get_secret(secret_id))