# dictionary-management
Správa řízených slovníků SYSNET


## Přehled
Verze 2 Správy řízených slovníků SYSNET byla přeprogramována do FastAPI. Služba je nyní daleko flexibilnější a rychlejší.

## Požadavky
Python 3.10+

## Použití
Chcete-li spustit vývojový server, proveďte tyto operace:
```
pip install -r requirements.txt
fastapi dev api/main.py

```

a otevřete prohlížeč na URL, kde najdete OpenAPI definici:

```
http://localhost:8000/docs
```


## Spouštění v Dockeru

Chcete-li spustit server v kontejneru Docker, proveďte následující příkazy:

```bash
# Sestavení obrazu
docker build -t sysnetcz/dictionaries:latest .

# spuštění kontejneru
docker run -p 8080:8000 sysnetcz/dictionaries:latest
```

## Zálohování a obnova
Správa řízených slovníků SYSNET ukládá data do NoSQL databáze MongoDB

### Zálohování

    docker exec mongo sh -c 'mongodump --archive --db=dictionaries --username <username> --password <password> --authenticationDatabase=admin > /backup/dictionaries.dump'
    docker cp mongo:/backup/dictionaries.dump .


### Obnova

    docker cp dictionaries.dump  mongo:/backup/
    docker exec mongo sh -c 'mongorestore --archive --db=dictionaries --username <username> --password <password> --authenticationDatabase=admin < /backup/dictionaries.dump'
