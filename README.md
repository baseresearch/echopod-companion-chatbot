<p align="center" width="100%">
<a href="https://t.me/MyEchopodBot" target="_blank"><img src="assets/logo.jpeg" alt="🐬 Echopod Companion" style="width: 50%; min-width: 300px; display: block; margin: auto;"></a>
</p>

# 🐬 Echopod - Companion Chatbot

This is the repo for the 🐬 Echopod - Companion Chatbot project, which aims to facilitate community participation in building largest publicly available conversational-style translation dataset between English and Burmese.

> If you want to contribute to the 🐬 Echopod bilingual dialog dataset project, please use our Telegram chatbot by following this link: [🐬 Echopod - Companion Chatbot](TBA).

## Overview

The current 🐬 Echopod - Companion Chatbot is designed to engage the Burmese community in collaborative annotation of the Echopod bilingual dialog dataset. It allows users to contribute translations from English to Burmese and score the quality of existing translations through a user-friendly interface accessible via Telegram app. This approach enables faster involvement compared to traditional PC annotation tools, making it more accessible for a wider range of contributors, including those who may have skipped the computer era.

The 🐬 Echopod - Companion Chatbot is still under development, and there are limitations that have to be addressed. We encourage users to provide feedback and report any issues or suggestions for improvements to help refine the chatbot and enhance the overall annotation experience.

Our initial release contains the source code, setup instructions, and usage guidelines for the chatbot. We intend to continuously update and improve the chatbot based on user feedback and the evolving needs of the 🐬 Echopod bilingual dialog dataset project.

**Please read our project overview for more details about the [🐬 Echopod bilingual dialog dataset](#🐬-echopod-bilingual-dialog-dataset-project) project and our vision for creating the largest publicly available conversational-style translation dataset between English and Burmese.**

## Features

- Contribution mode: Users can translate English sentences to Burmese.
- Voting mode: Users can rate the quality of English-Burmese sentence pairs on a scale of 1-5.
- Leaderboard: Displays the top 10 contributors based on their contribution count.
- ~~Automatic removal of low-quality translations: Translations with a score below 3 are removed and made available for contribution again.~~

## Setup

Running the code
To set up the Echopod chatbot for your own project, follow these steps:

1. Clone the repository:
   ```
   git clone https://github.com/baseresearch/echopod-companion-chatbot.git
   ```

2. Set up the PostgreSQL database:
   - Create a new PostgreSQL database for the chatbot.
   - Execute the SQL commands in the `setup.sql` file to create the necessary tables and indexes.

3. Configure the bot:
   - Create a `.env` file in the project root directory.
   - Add the following environment variables to the `.env` file:
      - `TELEGRAM_BOT_TOKEN`=your_telegram_bot_token
      - `DB_NAME`=your_database_name
      - `DB_USER`=your_database_user
      - `DB_PASSWORD`=your_database_password
      - `DB_HOST`=your_database_host
   - Replace the placeholders with your actual values.

4. Install the required dependencies:
   ```
   pip install python-telegram-bot psycopg2 python-dotenv
   ```

5. Run the bot:
   ```
   python bot.py
   ```

**Make sure you have Python and PostgreSQL installed on your system before running the bot.**

## Usage

1. Start a conversation with the bot on Telegram.
2. Use the `/start` command to begin and choose a mode (`/contribute` or `/vote`).
3. In contribution mode, the bot will send you an English sentence to translate. Provide your Burmese translation as a reply.
4. In voting mode:
   - On your first vote, the bot will show you the voting rules.
   - Click "OK" to start voting.
   - The bot will send you an English-Burmese translation pair.
   - Rate the quality of the translation on a scale of 1-5.
5. Use the `/leaderboard` command to view the top 10 contributors.

### Contributing

Contributions are welcome! If you find any issues or have suggestions for improvements, please open an issue or submit a pull request.

### Authors

The 🐬 Echopod - Companion Chatbot is developed and maintained by the team at [Base Technology](https://www.basetechnology.xyz/).

### Citation
Please cite the repo if you use the code or resources from this project.

```
@misc{echopod-chatbot,
author = {Swan Htet Aung, Base Technology},
title = {🐬 Echopod - Companion Chatbot},
year = {2023},
publisher = {GitHub},
journal = {GitHub repository},
howpublished = {\url{https://github.com/baseresearch/echopod-companion-chatbot}},
}
```

### Acknowledgements

We thank all the contributors and community members who have supported and participated in the 🐬 Echopod bilingual dialog dataset project. Your contributions are invaluable in creating the largest publicly available conversational-style translation dataset between English and Burmese.

### License

This project is licensed under the [Apache-2.0 license](LICENSE).

---

## 🐬 Echopod Bilingual Dialog Dataset Project

The 🐬 Echopod bilingual dialog dataset project aims to create the largest publicly available conversational-style translation dataset between English and Burmese (ENG <> MM). [Base Technology](https://www.basetechnology.xyz/) is developing this dataset from the ground up by collecting conversational-style data from various sources, including movie subtitles, novel dialogs, wikipedia articles, and more. The collected data undergoes machine translation using 🐬 Echopod's translation model, and the community is invited to contribute to the refinement and validation of the translations.