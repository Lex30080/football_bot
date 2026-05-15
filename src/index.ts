import "dotenv/config"
import { Telegraf } from "telegraf"

const bot = new Telegraf(process.env.BOT_TOKEN!)

bot.start((ctx) => {
  ctx.reply("⚽ Football bot is running!")
})

bot.launch()

console.log("Bot started")