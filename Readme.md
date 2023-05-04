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
       +-----------------------------------------+                                                                                                                           
       |   DigitalOcean Droplet: Wordpress       |                                            +----------------------------------------------------+                         
       |                                         |                                            | External Services                                  |                         
       -------------------------------------------                                            | +------------+      +-----------------------------+|                         
       | +------------+ +-------------------+    |              +----------------------+      | |            |    --| sjsuparkingstatus.sjsu.edu  ||                         
       | | New Relic: | |                   |    |              |      End Users:      |      | |            |    | +-----------------------------+|                         
       | | Infra      | |     WordPress     |    |              |       Browser        |      | |   OpenAI   |    | +-----------------------------+|                         
       | | PHP        | |     Front-end     <------------------->       Mobile         |      | |            |    --|   sjsu.doublemap.com/map    ||                         
       | | Apache     | |                   |    |              |       Discord        |      | |            |    | +-----------------------------+|                         
       | |            | |                   <-------------      +----------------^-----+      | +--^---------+    |                                |                         
       | +------------+ +-------------------+    |       |                       |            |    |              |                                |                         
       |                                         |       |                       -------      |    |              |                                |                         
       |                                         |       |                             |      +----|--------------|--------------------------------+                         
       +-----------------------------------------+       |                             |           |              |                                                          
       +-------------------------------------------------|-----------------------------|-----------|--------------|-----------------+                                        
       |  Docker Environment (network isolated)          |                             |           |              |                 |                                        
       |+------------------------------------------+  +--|-----------------------------|-----------|--------------|----------------+|                                        
       ||     Monitoring and Control Services      |  |  |   ParkingSucks Microservices|           |              |                ||                                        
       ||                                          |  |  |                             |           |              |                ||                                        
       ||                                          |  |  v-------------+    +----------v--+    +---v---------+    v-------------+  ||                                        
       || +-------------+                          |  |  |             |    |             |    |             |    |             |  ||                                        
       || |             |                          |  |  | Parking-API |    | Discord-Bot |    | Completion- |    | Web-Scraper |  ||                                        
       || |  Jenkins    |                          |  |  |             <---->             |    |   Manager   |    |             |  ||                                        
       || |             |<---|                     |  |  |             |    |             |    |             |    |             |  ||                                        
       || |             |    |                     |  |  +------^---^--+    +-------------+    +---^---------+    +---|---------+  ||                                        
       || +-------------+    |                     |  |         |   |                              |                  |            ||                                        
       || +-------------+    |    +-------------+  |  |         |   |                              |                  |            ||                                        
       || |             |    |    |             |  |  |         |   --------------------------------                  |            ||                                        
       || | Portainer   |<---|    |    NGINX    |  |  |         |         +---------------------------------+         |            ||                                        
       || |             |    |    |             |  |  |         |         |MariaDB                          |         |            ||                                        
       || |             |    |<----             |  |  |         |----------     scraped_data.sjsu           <---------|            ||                                        
       || +-------------+    |    +-------------+  |  |                   |     scraped_data.sjsu-shuttles  |                      ||                                        
       || +-------------+    |    +-------------+  |  |                   |     scraped_data.WordPress      |                      ||                                        
       || |             |    |    | New Relic:  |  |  |                   |     psskeds.skeds               |                      ||                                        
       || | PHPMyAdmin  |    |    | Infra       |  |  |                   +---------------------------------+                      ||                                        
       || |             |<---|    |             |  |  |                                                                            ||                                        
       || |             |         |             |  |  |                                                                            ||                                        
       || +-------------+         +-------------+  |  |                                                                            ||                                        
       |+------------------------------------------+  +----------------------------------------------------------------------------+|                                        
       +----------------------------------------------------------------------------------------------------------------------------+                                        
```

## Sequence Diagram
```
+---------------------------------------------------------------------------------------------------------------------------------------------------+
|/completion                              OpenAI                                                                                OpenAI      OpenAI  |
|endpoint           Answer Chain        Moderation      Map Chain      Parking Chain      Parking API         MariaDB           GPT-3       GPT-4   |
|      |------AuthN------>|                 |               |                |                  |                |                |           |     |
|      |                  |                 |               |                |                  |                |                |           |     |
|      |                  |<----Content---->|               |                |                  |                |                |           |     |
|      |                  |<----------------------------------GPT moderation/content/logic check--------------------------------->|           |     |
|      |                  |<--Determine garage distances--->|<---------------Extract location from natural language-------------->|           |     |
|      |                  |-------Get parking fullness, shuttle times------->|                  |                |                |           |     |
|      |                  |                 |               |                |<-----Extract API calls from natrual language------>|           |     |
|      |                  |                 |               |                |<------Call------>|<---Read only---|                |           |     |
|      |                  |<-----------Return table of relevant parking information-------------|                |                |           |     |
|      |                  |<------------Use known user data, parking information, location to garage distances and form an answer------------>|     |
|      |<-Return to user--|                 |               |                |                  |                |                |           |     |
+---------------------------------------------------------------------------------------------------------------------------------------------------+
```

## Prompts
TODO

Data scraped from [SJSU Parking Spots](http://sjsuparkingstatus.sjsu.edu/GarageStatus)
