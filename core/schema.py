import graphene
import user.schema
import insights.schema

class Query (
  user.schema.Query,
  insights.schema.Query,
  graphene.ObjectType
):
  pass

class Mutation(
  user.schema.Mutation,
  insights.schema.Mutation,
  graphene.ObjectType
):
  pass

schema = graphene.Schema(query=Query, mutation=Mutation)