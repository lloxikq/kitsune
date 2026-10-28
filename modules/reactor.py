# meta developer: @lloxikq
# meta banner: https://i.pinimg.com/1200x/6d/83/3e/6d833ecb875bbeea1ccde75d90b9bcc3.jpg
# meta pic: https://i.pinimg.com/736x/e8/f8/5e/e8f85edf067f466a70e56d846b8a83e6.jpg
# scope: hikka_only
# requires: emoji asyncio

__version__ = (0, 9, 9)

import emoji
import asyncio
import logging
from telethon.tl.functions.messages import GetAvailableReactionsRequest
from .. import loader, utils

ADD = "add"
DELETE = "del"
LIST = "list"

logger = logging.getLogger(__name__)

@loader.tds
class Reactor(loader.Module):
    """Automaticly reacts to messages from selected users"""
    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "def_emoji",
                "🤡",
                lambda: "Reaction default emoji",
                validator=loader.validators.Emoji(length=1)
            ),
            loader.ConfigValue(
                "delay",
                0,
                lambda: "Delay before react",
                validator=loader.validators.Integer(minimum=0)
            )
        )

    strings = {
        "name": "reactor",
        "added": "{user} added | {emoji}",
        "removed": "{user} removed",
        "no_args": f"no args specified \nUsage .rc <code>{ADD}</code>/<code>{DELETE}</code>/<code>{LIST}</code>",
        "no_user": "user not selected. Reply to user's message or specify username/ID",
        "not_found": "user {user} was not on the list. Nothing to remove",
        "list_empty": "list is empty"
    }
    

    @staticmethod
    def name(user) -> str:
        return f"@{user.username}" if user.username else user.first_name
        

    @staticmethod
    def is_emoji(text: str) -> bool:
        return bool(text) and emoji.emoji_list(text) and ''.join(
            item['emoji'] for item in emoji.emoji_list(text)
        ) == text

    async def _allowed_emoji(self) -> set:
        res = await self._client(GetAvailableReactionsRequest(hash=0))
        return {r.reaction for r in res.reactions if not r.inactive}
    
    async def _get_user_id(self, message):
        args = utils.get_args_raw(message)
        if not args:
            logger.error("no args specified")
            return None

        try:
            entity = await self._client.get_entity(args.split('@', 1)[1].split()[0])
            return entity.id
        except IndexError: pass
        except Exception as e:
            logger.error(e)

        reply = await message.get_reply_message()
        if reply:
            return reply.sender_id

        return await utils.answer(message, self.strings["no_user"])
        
    async def rccmd(self, message):
        """reactor test"""
        args = utils.get_args(message)
        
        if len(args) == 0:
            return await utils.answer(message, self.strings["no_args"])
        
        users = self.get("users", {})

        if args[0] == LIST:
            entries = []
            for user_id, value in users.items():
                entity = await self._client.get_entity(user_id)
                entries.append((self.name(entity), value))

            user_list = "\n".join(f"{value} | {name}" for name, value in entries)
            if user_list:
                # await utils.answer(message, f"<pre>{utils.escape_html(user_list)}</pre>")
                await utils.answer(message, user_list)
            else:
                await utils.answer(message, self.strings["list_empty"])
            return
        
        user = await self._client.get_entity(await self._get_user_id(message))

        if args[0] == ADD:
            if len(args) >= 2 and self.is_emoji(args[2]) and args[2] in await self._allowed_emoji():
                users[user.id] = args[2]
            else:
                if user.id not in users.keys():
                    users[user.id] = self.config["def_emoji"]
                logger.warning("Emoji is not provided or not allowed, using default")
            await utils.answer(message, self.strings("added").format(user=self.name(user), emoji=users[user.id]))
        
        elif args[0] == DELETE:
            removed = users.pop(user.id, None)
            if removed:
                await utils.answer(message, self.strings("removed").format(user=self.name(user)))
            else:
                await utils.answer(message, self.strings("not_found").format(user=self.name(user)))

        
        
        self.set("users", users)
        await message.delete()
    
    @loader.watcher(only_messages=True)
    async def react(self, msg):
        users = self.get("users")
        if users and msg.sender_id in self.get("users"):
            await asyncio.sleep(self.config["delay"])
            await self._client.send_reaction(msg.chat_id, msg.id, self.get("users")[msg.sender_id])