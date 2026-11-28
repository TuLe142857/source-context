const axios = require("axios");

class ProductsClient {
  constructor() {
    this.client = axios.create({ baseURL: "http://users:3000/api/v1" });
  }

  list() {
    return this.client.get("/products");
  }
}

module.exports = { ProductsClient };
