import asyncio
import logging

from pymodbus.client import AsyncModbusTcpClient

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def modbus_operations():
    logger.debug("Creating Modbus TCP client for 10.0.0.78:502")

    async with AsyncModbusTcpClient(host="10.0.0.78", port=502) as client:
        try:
            logger.debug("Attempting to connect to device")
            connected = await client.connect()

            if connected:
                logger.info("Successfully connected to device")

                # Read operation (unchanged)
                logger.debug("Reading 1 register from address 2, device 20")
                result = await client.read_holding_registers(
                    address=2, count=1, device=20
                )

                if result.isError():
                    logger.error("Error reading register: %s", result)
                else:
                    logger.info(
                        "Successfully read register value: %s", result.registers[0]
                    )
                    print(result.registers[0])

                # Write operation using write_register (function code 6)
                logger.debug(
                    "Writing value 2 to register at address 2, device 20 using write_register"
                )
                result = await client.write_register(address=2, value=2, device=20)

                if result.isError():
                    logger.error(
                        "Error writing register with write_register: %s", result
                    )
                else:
                    logger.info("Successfully wrote register with write_register")

                # Write operation using write_registers (function code 16)
                logger.debug(
                    "Writing value 5 to 1 register at address 2, device 20 using write_registers"
                )
                result = await client.write_registers(address=2, values=[5], device=20)

                if result.isError():
                    logger.error(
                        "Error writing register with write_registers: %s", result
                    )
                else:
                    logger.info("Successfully wrote register with write_registers")

            else:
                logger.error("Failed to connect to device")

        except Exception as e:
            logger.exception("An error occurred: %s", str(e))
            raise

    logger.info("Connection closed automatically by context manager")


if __name__ == "__main__":
    logger.info("Starting Modbus operations")
    try:
        asyncio.run(modbus_operations())
        logger.info("Modbus operations completed successfully")
    except Exception as e:
        logger.error("Program terminated with error: %s", str(e))
