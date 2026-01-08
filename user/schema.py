import graphene
from user.graphql.mutations import CreateProfile, UpdateLocation, UpdateProfile
from user.graphql.queries import UserQueries


class Query(UserQueries, graphene.ObjectType):
    """User app queries"""

    pass


class Mutation(graphene.ObjectType):
    """User app mutations"""

    # Profile Mutations
    create_profile = CreateProfile.Field()
    update_profile = UpdateProfile.Field()
    update_location = UpdateLocation.Field()
