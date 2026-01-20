import account.schema
import authentication.schema
import graphene
import insights.schema
import travel.schema
import user.schema


class Query(
    authentication.schema.Query,
    user.schema.Query,
    account.schema.Query,
    insights.schema.Query,
    travel.schema.Query,
    graphene.ObjectType,
):
    pass


class Mutation(
    authentication.schema.Mutation,
    user.schema.Mutation,
    account.schema.Mutation,
    insights.schema.Mutation,
    travel.schema.Mutation,
    graphene.ObjectType,
):
    pass


schema = graphene.Schema(query=Query, mutation=Mutation)
