# ParkingSucks.com

## Description
This repo contains 4 micro-services:
- **scraper**: Scrapes data from the web and stores it in the DB. 
- **parking-api**: An apy which retrieves parking information or runs a given SQL query (w/ API key)
- **discord-bot**: A simple discord bot that listens for messages and calls the completion manager
- **completion-manager**: Checks safety of request, generates a SQL query and returns a human readable final answer
Assume all code generated fully, mostly or in part by GPT3.5 or GPT4. Exact prompts used to generate or modify code will be added at a later date.

## Sequence Diagram
```
User              Discord             ParkingSucksBot             CompletionAPI           ModerationEP                    GPT               Parking-API
 |                    |                    |                          |                         |                          |                     |
 |-------Log in------>|                    |                          |                         |                          |                     |
 |                    |                    |                          |                         |                          |                     |
 |---Ask question---->|                    |                          |                         |                          |                     |
 |                    |--Forward questio-->|                          |                         |                          |                     |
 |                    |                    |----Call CompletionAPI--->|                         |                          |                     |
 |                    |                    |                          |-->Validate API Key      |                          |                     |
 |                    |                    |                          |<-----------------|      |                          |                     |
 |                    |                    |                          |------Check Moderation-->|                          |                     |
 |                    |                    |                          |------------------Generate SQL Query--------------> |                     |
 |                    |                    |                          |                         |                          |---Run SQL Query---->|
 |                    |                    |                          |<-----------------------------Return query results------------------------|
 |                    |                    |                          |--------------Generate final answer strin---------->|                     |
 |                    |                    |                          |<------------Return Answer String-------------------|                     |
 |                    |                    |                          |<-Return Answer String---|                          |                     |
 |                    |                    |<--Post Answer to Discord-|                         |                          |                     |
 |                    |<--Display Answer---|                          |                         |                          |                     |
```

## Prompts
TODO

Data scraped from [SJSU Parking Spots](http://sjsuparkingstatus.sjsu.edu/GarageStatus)
