import { Controller, Get, Param, Post } from "@nestjs/common";

@Controller("accounts")
export class AccountsController {
  @Get(":id")
  findOne(@Param("id") id: string) {
    return { id };
  }

  @Post()
  create() {
    return {};
  }
}
