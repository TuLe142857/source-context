import { NestFactory } from "@nestjs/core";

async function bootstrap(module: unknown) {
  const app = await NestFactory.create(module);
  app.setGlobalPrefix("api");
  await app.listen(3000);
}

bootstrap({});
