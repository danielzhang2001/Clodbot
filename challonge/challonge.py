# TODO: Implement functionality for challonge

# from challonge import api


# @bot.command(name='match list')
# def index(tournament, **params):
#     """Retrieve a tournament's match list."""
#     return api.fetch_and_parse(
#         "GET",
#         "tournaments/%s/matches" % tournament,
#         **params)


# @bot.command(name='show')
# def show(tournament, match_id):
#     """Retrieve a single match record for a tournament."""
#     return api.fetch_and_parse(
#         "GET",
#         "tournaments/%s/matches/%s" % (tournament, match_id))


# @bot.command(name='update')
# def update(tournament, match_id, **params):
#     """Update/submit the score(s) for a match."""
#     api.fetch(
#         "PUT",
#         "tournaments/%s/matches/%s" % (tournament, match_id),
#         "match",
#         **params)
