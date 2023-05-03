# ParkingSucks.com

## Description
This repo contains 4 micro-services:
- **scraper**: Scrapes data from the web and stores it in the DB. 
- **parking-api**: An apy which retrieves parking information or runs a given SQL query (w/ API key)
- **discord-bot**: A simple discord bot that listens for messages and calls the completion manager
- **completion-manager**: Checks safety of request, generates a SQL query and returns a human readable final answer
Assume all code generated fully, mostly or in part by GPT3.5 or GPT4. Exact prompts used to generate or modify code will be added at a later date.

## Component Diagram
```
       +--------------------------------------+                                                                                                                              
       |   DigitalOcean Droplet: Wordpress    |                                               +----------------------------------------------------+                         
       |                                      |                                               | External Services                                  |                         
       ----------------------------------------                                               | +------------+      +-----------------------------+|                         
       | +------------+ +-------------------+ |                 +----------------------+      | |            |    --- sjsuparkingstatus.sjsu.edu  ||                         
       | | New Relic: | |                   | |                 |      End Users:      |      | |            |    | +-----------------------------+|                         
       | | Infra      | |     WordPress     | |                 |       Browser        |      | |   OpenAI   |    | +-----------------------------+|                         
       | | PHP        | |     Front-end     <------------------->       Mobile         |      | |            |    ---   sjsu.doublemap.com/map    ||                         
       | | Apache     | |                   | |                 |       Di cord        |      | |            |    | +-----------------------------+|                         
       | |            | |                   <-------------      +----------------|-----+      | +--^------|--+    |                                |                         
       | +------------+ +-------------------+ |          |                       |            +----|------|-------|--------------------------------+                         
       |                                      |          |                       -------           |      |       |                                                          
       |                                      |          |                             |           |      |       |                                                          
       +--------------------------------------+          |                             |           |      |       |                                                          
                                                         |                             |           |      |       |                                                          
       +-------------------------------------------------|-----------------------------|-----------|------|-------|-----------------+                                        
       |+------------------------------------------+  +--|-----------------------------|-----------|------|-------|----------------+|                                        
       ||     Monitoring and Control Services      |  |  |   ParkingSucks Microservices|           |      |       |                ||                                        
       ||                                          |  |  |                             |           |      |       |                ||                                        
       ||                                          |  |  v-------------+    +----------v--+    +---|------v--+    v-------------+  ||                                        
       || +-------------+                          |  |  |             |    |             |    |             |    |             |  ||                                        
       || |             |                          |  |  | Parking-API |    | Discord-Bot |    | Completion- |    | Web-Scraper |  ||                                        
       || |  Jenkins    |                          |  |  |             <--- |             |    |   Manager   |    |             |  ||                                        
       || |             |<---|                     |  |  |             |    |             |    |             |    |             |  ||                                        
       || |             |    |                     |  |  +------^---^--+    +-------------+    +---^---------+    +---|---------+  ||                                        
       || +-------------+    |                     |  |         |   |                              |                  |            ||                                        
       || +-------------+    |    +-------------+  |  |         |   --------------------------------                  |            ||                                        
       || |             |    |    |             |  |  |         |                                                     |            ||                                        
       || | Portainer   |<---|    |    NGINX    |  |  |         |         +---------------------------------+         |            ||                                        
       || |             |    |    |             |  |  |         |         |MariaDB                          |         |            ||                                        
       || |             |    |<----             |  |  |         |--------->     scraped_data.sjsu           <---------|            ||                                        
       || +-------------+    |    +-------------+  |  |                   |     scraped_data.sjsu-shuttles  |                      ||                                        
       || +-------------+    |    +-------------+  |  |                   |     scraped_data.sjsu_wordpress |                      ||                                        
       || |             |    |    | New Relic:  |  |  |                   |     scraped_data.WordPress      |                      ||                                        
       || | PHPMyAdmin  |    |    | Infra       |  |  |                   |                                 |                      ||                                        
       || |             |<---|    |             |  |  |                   |     psskeds.skeds               |                      ||                                        
       || |             |         |             |  |  |                   |                                 |                      ||                                        
       || +-------------+         +-------------+  |  |                   +---------------------------------+                      ||                                        
       |+------------------------------------------+  +----------------------------------------------------------------------------+|                                        
       +----------------------------------------------------------------------------------------------------------------------------+                                        ```

## Sequence Diagram
```
User              Discord             ParkingSucksBot             CompletionAPI           ModerationEP                    GPT               Parking-API
 |                    |                    |                          |                         |                          |                     |
 |-------Log in------>|                    |                          |                         |                          |                     |
 |---Ask question---->|                    |                          |                         |                          |                     |
 |                    |-Forwards question->|                          |                         |                          |                     |
 |                    |                    |----Call CompletionAPI--->|                         |                          |                     |
 |                    |                    |                          |-->Validate API Key      |                          |                     |
 |                    |                    |                          |<-----------------|      |                          |                     |
 |                    |                    |                          |------Check Moderation-->|                          |                     |
 |                    |                    |                          |------------------Generate SQL Query--------------> |                     |
 |                    |                    |                          |<----------------Return SQL query-------------------|                     |
 |                    |                    |                          |-------------------------------Run SQL Query----------------------------->|
 |                    |                    |                          |<-----------------------------Return query results------------------------|
 |                    |                    |                          |--------------Generate final answer string--------->|                     |
 |                    |                    |                          |<------------Return answer String-------------------|                     |
 |                    |                    |<--Return answer via API--|                         |                          |                     |
 |                    |<--Display Answer---|                          |                         |                          |                     |
```

## Prompts
TODO

Data scraped from [SJSU Parking Spots](http://sjsuparkingstatus.sjsu.edu/GarageStatus)
