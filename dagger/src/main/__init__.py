import dagger
from dagger import dag, function, object_type


@object_type
class RemultCli:
    @function
    def test_db_srv(self, source: dagger.Directory) -> dagger.Service:
        """Return a Postgres DB ready for running tests"""
        return (
            dag.container()
			.from_("postgres:14-alpine")
			.with_env_variable("POSTGRES_PASSWORD", "postgres")
			.with_env_variable("POSTGRES_USER", "postgres")
			.with_env_variable("POSTGRES_DB", "bookstore_db")
			#.with_mounted_cache("/var/lib/postgresql/data", dag.cache_volume("my-postgres"))
			.with_exposed_port(5432)
			.as_service()
        )

    @function
    async def test(self, source: dagger.Directory) -> str:
        """Return the result of running unit tests"""
        return await (
            self.build_env(source)
            .with_exec(["bash", "-c", "psql postgresql://postgres:postgres@db:5432/bookstore_db -a -f scripts/db/bookstore-schecma.sql"])
            .with_exec(["pnpm", "test:ci"])
            .stdout()
        )

    @function
    def build_env(self, source: dagger.Directory) -> dagger.Container:
        """Build a ready-to-use development environment complete with DB"""
        node_cache = dag.cache_volume("node")
        dist_cache = dag.cache_volume("dist")
        postgres_srv = self.test_db_srv(source)
        return (
            dag.container()
            .from_("node:21-slim")
            .with_directory("/src", source)
            .with_mounted_cache("/src/node_modules", node_cache)
            .with_workdir("/src")
            .with_exec(["npm", "install", "-g", "pnpm"])
            .with_exec(["pnpm", "install"])
            .with_mounted_cache("/src/dist", dist_cache)
            .with_exec(["pnpm", "build"])
            .with_exec(["apt", "update"])
            .with_exec(["apt", "install", "postgresql-client", "-y"])
            .with_service_binding("db", postgres_srv)
        )