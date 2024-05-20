import boto3
from datetime import datetime, timedelta
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd


# Retrieve data from DynamoDB
dynamodb = boto3.resource("dynamodb", region_name="us-east-2")
table = dynamodb.Table("echopod_User")
response = table.scan(
    ProjectionExpression="user_id, auto_contribute, auto_vote, avg_interaction_interval, contribute_mode, contribute_text_id, contributions, last_interaction_session_time, last_interaction_time, paused, saw_best_practices, username, votings"
)
items = response["Items"]


def plot_something():

    # Extract relevant data from the items
    interaction_intervals = []
    avg_interaction_intervals = []
    filtered_avg_interaction_intervals = []
    contributions = []
    votings = []
    auto_contribute = []
    auto_vote = []

    for item in items:
        if item["user_id"] == "1":
            continue

        if "last_interaction_session_time" in item and "last_interaction_time" in item:
            last_interaction_session_time = datetime.fromisoformat(
                item["last_interaction_session_time"]
            )
            last_interaction_time = datetime.fromisoformat(
                item["last_interaction_time"]
            )
            interaction_interval = (
                last_interaction_time - last_interaction_session_time
            ).total_seconds() / 60
            interaction_intervals.append(interaction_interval)

        if "avg_interaction_interval" in item and (
            "votings" in item or "contributions" in item
        ):
            if int(item.get("votings", 0)) > 0 or int(item.get("contributions", 0)) > 0:
                avg_interaction_interval = float(item["avg_interaction_interval"]) / 60
                filtered_avg_interaction_intervals.append(avg_interaction_interval)

        if "contributions" in item and "votings" in item:
            contributions.append(int(item["contributions"]))
            votings.append(int(item["votings"]))

    # User Engagement Metrics
    avg_interaction_interval = np.mean(avg_interaction_intervals)
    avg_contribution = np.mean(contributions)
    avg_voting = np.mean(votings)

    print(f"Average Interaction Interval: {avg_interaction_interval:.2f} minutes")
    print(f"Average Contribution: {avg_contribution:.2f}")
    print(f"Average Voting: {avg_voting:.2f}")

    # User Segmentation
    def segment_users(data, threshold):
        frequent_users = [x for x in data if x >= threshold]
        infrequent_users = [x for x in data if x < threshold]
        return frequent_users, infrequent_users

    frequent_contributors, infrequent_contributors = segment_users(
        contributions, avg_contribution
    )
    frequent_voters, infrequent_voters = segment_users(votings, avg_voting)

    print(f"Frequent Contributors: {len(frequent_contributors)}")
    print(f"Infrequent Contributors: {len(infrequent_contributors)}")
    print(f"Frequent Voters: {len(frequent_voters)}")
    print(f"Infrequent Voters: {len(infrequent_voters)}")

    # Temporal Analysis
    interaction_timestamps = [
        datetime.fromisoformat(item["last_interaction_time"])
        for item in items
        if "last_interaction_time" in item
    ]
    interaction_hours = [timestamp.hour for timestamp in interaction_timestamps]

    # sns.set(style="darkgrid")
    # plt.figure(figsize=(10, 6))
    # sns.histplot(interaction_hours, bins=24, kde=True, color="skyblue", edgecolor="black")
    # plt.xlabel("Hour of the Day")
    # plt.ylabel("Interaction Frequency")
    # plt.title("Interaction Frequency by Hour")
    # plt.tight_layout()
    # plt.show()

    # # Correlation Analysis
    # sns.set(style="whitegrid")
    # plt.figure(figsize=(10, 6))
    # sns.scatterplot(x=contributions, y=votings, color="coral", alpha=0.6)
    # plt.xlabel("Contributions")
    # plt.ylabel("Votings")
    # plt.title("Correlation between Contributions and Votings")
    # plt.tight_layout()
    # plt.show()

    # sns.set(style="whitegrid")
    # plt.figure(figsize=(10, 6))
    # sns.histplot(
    #     filtered_avg_interaction_intervals,
    #     bins=20,
    #     kde=True,
    #     color="skyblue",
    #     edgecolor="black",
    # )
    # plt.xlabel("Average Interaction Interval (minutes)")
    # plt.ylabel("Frequency")
    # plt.title(
    #     "Distribution of Average Interaction Intervals (Users with Votings or Contributions)"
    # )
    # plt.tight_layout()
    # plt.show()


def interaction_since_bot_publish():
    # Interaction Frequency Since Bot Release
    bot_release_date = datetime(
        2024, 4, 19
    )  # Assuming the bot was released on January 1, 2023
    interaction_dates = [
        datetime.fromisoformat(item["last_interaction_time"]).date()
        for item in items
        if "last_interaction_time" in item
    ]

    date_range = pd.date_range(
        start=bot_release_date.date(), end=datetime.now().date(), freq="D"
    )
    interaction_counts = (
        pd.Series(interaction_dates)
        .groupby(interaction_dates)
        .count()
        .reindex(date_range, fill_value=0)
    )

    sns.set(style="darkgrid")
    plt.figure(figsize=(12, 6))
    ax = sns.lineplot(x=date_range, y=interaction_counts, color="skyblue")

    # Set x-tick labels to display only the date part
    date_labels = [d.strftime("%Y-%m-%d") for d in date_range]
    plt.xticks(date_range, date_labels, rotation=45)

    plt.xlabel("Date")
    plt.ylabel("Interaction Frequency")
    plt.title("Interaction Frequency Since Bot Release")
    plt.tight_layout()
    plt.show()


interaction_since_bot_publish()


def retention_chart():
    # Retention Chart
    first_interaction_dates = {}
    for item in items:
        if 'user_id' in item and 'last_interaction_time' in item:
            user_id = item['user_id']
            interaction_date = datetime.fromisoformat(item['last_interaction_time']).date()
            if user_id not in first_interaction_dates:
                first_interaction_dates[user_id] = interaction_date

    retention_data = []
    for user_id, first_date in first_interaction_dates.items():
        user_interactions = [datetime.fromisoformat(item['last_interaction_time']).date() for item in items if 'user_id' in item and item['user_id'] == user_id]
        for days_since_first in range(7):
            target_date = first_date + timedelta(days=days_since_first)
            if target_date in user_interactions:
                retention_data.append((user_id, days_since_first, 1))
            else:
                retention_data.append((user_id, days_since_first, 0))

    retention_df = pd.DataFrame(retention_data, columns=['User ID', 'Days Since First Interaction', 'Retained'])
    retention_df['Days Since First Interaction'] = retention_df['Days Since First Interaction'].astype(int)
    retention_pct = retention_df.groupby('Days Since First Interaction')['Retained'].mean()

    sns.set(style="darkgrid")
    plt.figure(figsize=(10, 6))
    ax = sns.lineplot(x=retention_pct.index, y=retention_pct.values, color="skyblue", marker='o')

    plt.xlabel('Days Since First Interaction')
    plt.ylabel('Retention Percentage')
    plt.title('User Retention')
    plt.xticks(range(7), range(7))
    plt.ylim(0, 1)
    plt.gca().yaxis.set_major_formatter(mtick.PercentFormatter(1.0))

    for x, y in zip(retention_pct.index, retention_pct.values):
        plt.text(x, y, f"{y:.0%}", ha='center', va='bottom')

    plt.tight_layout()
    plt.show()

#retention_chart()