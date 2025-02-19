import asyncio
import websockets

zones = (
    "Madrid", "Barcelona", "Valencia", "Sevilla", "Zaragoza", "Málaga", "Murcia", "Palma", "Bilbao", "Alicante",
    "París", "Marsella", "Lyon", "Toulouse", "Niza", "Nantes", "Estrasburgo", "Montpellier", "Burdeos", "Lille",
    "Berlín", "Hamburgo", "Múnich", "Colonia", "Fráncfort", "Stuttgart", "Düsseldorf", "Dresde", "Leipzig", "Hannover",
    "Roma", "Milán", "Nápoles", "Turín", "Palermo", "Génova", "Bolonia", "Florencia", "Bari", "Catania",
    "Londres", "Birmingham", "Manchester", "Glasgow", "Liverpool", "Edimburgo", "Leeds", "Bristol", "Sheffield", "Belfast",
    "Ámsterdam", "Róterdam", "La Haya", "Utrecht", "Eindhoven", "Groninga", "Arnhem", "Maastricht", "Tilburgo", "Breda",
    "Viena", "Graz", "Linz", "Salzburgo", "Innsbruck", "Klagenfurt", "Villach", "Wels", "Sankt Pölten", "Dornbirn",
    "Bruselas", "Amberes", "Gante", "Charleroi", "Lieja", "Brujas", "Namur", "Mons", "Lovaina", "Aalst",
    "Lisboa", "Oporto", "Braga", "Coímbra", "Funchal", "Faro", "Aveiro", "Évora", "Setúbal", "Leiria",
    "Oslo", "Bergen", "Trondheim", "Stavanger", "Kristiansand", "Drammen", "Tromsø", "Skien", "Ålesund", "Sandnes"
)


async def test_close_zones(zone):
    uri = "ws://localhost:8765"
    async with websockets.connect(uri) as websocket:

        await websocket.send(f"ADD_CLOSED:{zone}")
        message = await websocket.recv()
        print(f"Mensaje recibido: {message}")

async def test_open_zones(zone):    
    uri = "ws://localhost:8765"
    async with websockets.connect(uri) as websocket:

        await websocket.send(f"ADD_OPEN:{zone}")
        message = await websocket.recv()
        print(f"Mensaje recibido: {message}")
        

        


if __name__ == "__main__":
    #Ver que soporta trafico para reabrir
    for zone in zones:
        asyncio.run(test_open_zones(zone))

    #Ver que soporta trafico para cierre
    for zone in zones:
        asyncio.run(test_close_zones(zone))


    #Ver que soporta trafico real abriendo y cerrando muchas rutas
    for zone in zones:
        asyncio.run(test_open_zones(zone))
        asyncio.run(test_close_zones(zone))
        