import asyncio
import websockets
import json

async def test_websocket():
    try:
        async with websockets.connect("ws://localhost:8000/ws") as websocket:
            print("WebSocket连接成功！")
            # 发送订阅消息
            await websocket.send("subscribe:resource_stream")
            print("已发送订阅消息")
            
            # 接收3条消息
            for i in range(3):
                response = await websocket.recv()
                data = json.loads(response)
                print(f"\n收到消息 {i+1}:")
                print(f"时间戳: {data['timestamp']}")
                print(f"CPU使用率: {data['host']['cpu_percent']}%")
                print(f"内存使用率: {data['host']['mem_percent']}%")
                print(f"节点数量: {len(data['lobsters'])}")
                
    except Exception as e:
        print(f"连接失败: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())
