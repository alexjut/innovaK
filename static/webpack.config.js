const path = require("path");
const MiniCssExtractPlugin = require("mini-css-extract-plugin");

module.exports = (env, argv) => {
  const isProd = argv.mode === "production";

  return {
    context: __dirname,
    entry: {
      main: "./js/main.js",
      base: "./scss/base.scss",
    },
    output: {
      path: path.resolve(__dirname, "dist"),
      filename: "js/[name].js",
      clean: true,
    },
    module: {
      rules: [
        {
          test: /\.scss$/i,
          use: [
            MiniCssExtractPlugin.loader,
            {
              loader: "css-loader",
              options: {
                sourceMap: !isProd,
                url: false,
              },
            },
            {
              loader: "sass-loader",
              options: {
                sourceMap: !isProd,
              },
            },
          ],
        },
      ],
    },
    plugins: [
      new MiniCssExtractPlugin({
        filename: "css/[name].css",
      }),
    ],
    devtool: isProd ? false : "source-map",
  };
};