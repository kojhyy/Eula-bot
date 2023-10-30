from asyncio import sleep as async_sleep

import discord
from discord.ui import View
from uwutilities import String_tools

from commands.games.monopolyClasses.board import Board
from commands.games.monopolyClasses.data.const import CONST
from commands.games.monopolyClasses.data.squareData import SquareType
from commands.games.monopolyClasses.square import Tax
from commands.games.monopolyClasses.view.objectsView import ObjectsView
from commands.games.monopolyClasses.view.popupView import PopupView
from commands.games.monopolyClasses.view.sellPropertiesView import SellPropertiesView


class BoardView(View):
    def __init__(self, board: Board, game_msg: discord.Message):
        super().__init__(timeout=None)
        self.board = board
        self.game_msg = game_msg
        self.embed_color = 0x989eec

        self.popup_msg = None
        self.can_roll_dice = True
        self.userHasRolled = False


    @discord.ui.button(label="Lancer les dés", custom_id="dice", style=discord.ButtonStyle.primary, emoji="🎲")
    async def dice_button(self, interaction: discord.Interaction, button: discord.ui.Button):

        if interaction.user != self.board.getCurrentPlayer().discord:
            await interaction.response.send_message("Ce n'est pas votre tour !", ephemeral=True)
            return
        
        if self.IsPopupLaunched():
            await interaction.response.send_message("Vous devez répondre à la popup !", ephemeral=True)
            return
        
        if self.userHasRolled:
            await interaction.response.send_message("Vous avez déjà lancé les dés !", ephemeral=True)
            return
        
        if not self.can_roll_dice:
            await interaction.response.send_message("Vous ne pouvez pas lancer les dés maintenant !", ephemeral=True)
            return
        
        self.disableButton("dice")
        await self.updateView()

        self.can_roll_dice = False


        await interaction.response.defer()
        player = self.board.getCurrentPlayer()
        dice = self.board.rollDice(player)

        square = self.board.getSquareUnderPlayer(player)
        await self.showAction(f"<a:roll_dice:1162800533548056707> Vous avez obtenu {dice} !\n \
            Vous êtes sur la case {square.name}")
        await async_sleep(3)

        await self.executeSquare()


    @discord.ui.button(label="Augmenter les loyers", custom_id="upgrade", style=discord.ButtonStyle.secondary, emoji="📈")
    async def upgrade_button(self, interaction: discord.Interaction, button: discord.ui.Button):

        if interaction.user != self.board.getCurrentPlayer().discord:
            await interaction.response.send_message("Ce n'est pas votre tour !", ephemeral=True)
            return

        if self.IsPopupLaunched():
            await interaction.response.send_message("Vous devez répondre à la popup !", ephemeral=True)
            return
        
        user = self.board.getCurrentPlayer()
        upgradePrice = user.getPriceForUpgrade()

        if upgradePrice > user.money:
            await interaction.response.send_message(f"Vous n'avez pas assez d'argent !\nIl vous faut **{upgradePrice} $**", ephemeral=True)
            return
    
        if user.getNumberOfProperties() == 0:
            await interaction.response.send_message(f"Vous n'avez aucune propriété !", ephemeral=True)
            return
        
        await interaction.response.defer()
        embed = discord.Embed(title=f"Amélioration", description=f"Voulez-vous améliorer le loyer de 20% pour toutes vos propriétés actuelles pour **{upgradePrice} $** ?", color=self.embed_color)
        self.popup_msg = await self.game_msg.channel.send(embed=embed, view=PopupView(self.upgradeFunc, self.noFunc))


    @discord.ui.button(label="Finir le tour", custom_id="next", style=discord.ButtonStyle.red, emoji="⏭️", disabled=True)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):

        if interaction.user != self.board.getCurrentPlayer().discord:
            await interaction.response.send_message("Ce n'est pas votre tour !", ephemeral=True)
            return
        
        if self.IsPopupLaunched():
            await interaction.response.send_message("Vous devez répondre à la popup !", ephemeral=True)
            return
    
        if not self.userHasRolled:
            await interaction.response.send_message("Vous devez lancer les dés !", ephemeral=True)
            return

        await interaction.response.defer()
        await self.nextPlayer()
    

    @discord.ui.button(label="Vendre des propriétés", custom_id="sell_property", style=discord.ButtonStyle.secondary, row=2)
    async def sell_properties_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        
        if interaction.user != self.board.getCurrentPlayer().discord:
            await interaction.response.send_message("Ce n'est pas votre tour !", ephemeral=True)
            return
        
        if self.IsPopupLaunched():
            await interaction.response.send_message("Vous devez répondre à la popup !", ephemeral=True)
            return
    
        if self.board.getCurrentPlayer().getNumberOfProperties() == 0:
            await interaction.response.send_message("Vous n'avez aucune propriété !", ephemeral=True)
            return

        await interaction.response.defer()

        embed = discord.Embed(title="Vente de propriétés", description="Sélectionnées les propriétés que vous voulez vendre", color=self.embed_color)
        view = SellPropertiesView(self.board.getCurrentPlayer(), self.sellPropertiesFunc, self.noFunc)
        self.popup_msg = await self.game_msg.channel.send(embed=embed, view=view)


    @discord.ui.button(label="Utiliser un objet", custom_id="use_object", style=discord.ButtonStyle.secondary, row=2, emoji="🎒")
    async def object_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = self.board.getCurrentPlayer()
        if interaction.user != player.discord:
            await interaction.response.send_message("Ce n'est pas votre tour !", ephemeral=True)
            return
        
        if self.IsPopupLaunched():
            await interaction.response.send_message("Vous devez répondre à la popup !", ephemeral=True)
            return

        if player.getNumberOfObjects() == 0:
            await interaction.response.send_message("Vous n'avez aucun objet !", ephemeral=True)
            return

        await interaction.response.defer()

        embed = discord.Embed(title="Vos objets", description="Sélectionnez un objet à utiliser", color=self.embed_color)
        view = ObjectsView(player, player.objects, self.useObject, self.noFunc, False)
        self.popup_msg = await self.game_msg.channel.send(embed=embed, view=view)


    async def executeSquare(self):
        """When a player go on a square"""

        player = self.board.getCurrentPlayer()
        square = self.board.getSquareUnderPlayer(player)

        # 🏠 & 🚂
        if square.type == SquareType.PROPERTY or square.type == SquareType.RAILROAD:
            
            if self.board.getOwner(square) != None:
                playerHasPaid, square_rent = self.board.playerPayRent(player, square)

                await self.showAction(f"Vous avez payé **{square_rent} $** de loyer à {self.board.getOwner(square).discord.display_name} !")
                
                if not playerHasPaid:
                    # TODO : player has not enough money
                    await self.showAction(f"Vous n'avez pas assez d'argent pour payer le loyer !")
                    pass

            else:
                embed = discord.Embed(title=f"Achat", description=f"Voulez-vous acheter **{square.name}** pour **{square.price} $**", color=self.embed_color)
                view = PopupView(self.buyFunc, self.noFunc)

                self.popup_msg = await self.game_msg.channel.send(embed=embed, view=view)
                return

        # 🍀
        elif square.type == SquareType.LUCK:
            action = self.board.chance(player)
            await self.showAction(action)
            await async_sleep(2)

        # ⛓
        elif square.type == SquareType.GO_TO_JAIL:
            user = player
            old_position = user.position

            user.goToJail()
            self.board.movePlayerOnBoard(user, old_position)

            await self.showAction("Vous allez en prison !")

        # 💰
        elif square.type == SquareType.TAX:
            if player.Switzerland_account: # chance card
                await self.showAction("Vous avez un compte en Suisse, vous ne payez pas de taxe !")
            
            else:
                square: Tax
                player.loseMoney(square.price)
                await self.showAction(f"Vous avez payé **{square.price} $** de taxe !")
            
        elif square.type == SquareType.SHOP:
            await self.showAction("Vous êtes dans le magasin à objets !")
        
            embed = discord.Embed(title="Magasin", description="Sélectionnez un objet à acheter", color=self.embed_color)
            view = ObjectsView(player, self.board.objects, self.buyObjectFunc, self.noFunc, True)
            self.popup_msg = await self.game_msg.channel.send(embed=embed, view=view)


        self.userHasRolled = True
        self.enableButton("next")
        await self.updateView()
        await async_sleep(3)
        await self.showAction("...")


    async def showAction(self, action: str):
        await self.game_msg.edit(embed=self.getEmbed(action))


    def getEmbed(self, action: str = "...") -> discord.Embed:

        # embed
        embed = discord.Embed(title=f"Monopoly", color=self.embed_color)
        embed.add_field(name="Plateau", value=self.board.getBoardStr(), inline=False)
        
        currentPlayer = self.board.getCurrentPlayer()
        embed.add_field(name="Au tour de", value=f"{currentPlayer.discord.display_name} - {currentPlayer.money} $", inline=False)
        embed.add_field(name="Actions", value=action)
        
        return embed


    def IsPopupLaunched(self) -> bool:
        return self.popup_msg != None


    async def deletePopup(self):
        await self.popup_msg.delete()
        self.popup_msg = None


    async def nextPlayer(self):
        # reset
        self.board.nextPlayer()
        self.can_roll_dice = True
        self.userHasRolled = False
        await self.game_msg.edit(embed=self.getEmbed())

        player = self.board.getCurrentPlayer()

        # chance effects
        for effect in player.chance_effects.copy():
            action = effect.function(player)
            await self.showAction(action[-1])
            await async_sleep(3)
            await self.showAction("...")

            effect.turn -= 1
            if effect.turn == 0:
                player.chance_effects.remove(effect)

        # jail
        if player.jailTurn == 2:
            player.leaveJail()
            await self.showAction("Vous êtes libéré de prison !")
            await async_sleep(2)
            await self.showAction("...")

        if player.jail:
            player.jailTurn += 1
            await self.showAction("Vous êtes en prison !")
            
            if player.jailCard:
                embed = discord.Embed(title=f"Sortie de prison", description=f"Voulez-vous utiliser votre carte de sortie de prison ?", color=self.embed_color)
                view = PopupView(self.buyFunc, self.noJailFunc)

                self.popup_msg = await self.game_msg.channel.send(embed=embed, view=view)
                return 
            else:
                embed = discord.Embed(title=f"Sortie de prison", description=f"Voulez-vous payer **{CONST.JAIL_FEE} $** pour sortir de prison ?", color=self.embed_color)
                view = PopupView(self.payJailFunc, self.noJailFunc)

                self.popup_msg = await self.game_msg.channel.send(embed=embed, view=view)

        self.disableButton("next")
        self.enableButton("dice")
        await self.updateView()


    async def buyFunc(self, interaction: discord.Interaction):
        if interaction.user != self.board.getCurrentPlayer().discord:
            await interaction.response.send_message("Ce n'est pas votre tour !", ephemeral=True)
            return

        user = self.board.getCurrentPlayer()
        square = self.board.getSquareUnderPlayer(user)
        self.board.buyProperty(user, square)

        await self.deletePopup()

        await self.showAction(f"Vous avez acheté **{square.name}** !")
        self.userHasRolled = True
        self.enableButton("next")
        await self.updateView()
        await async_sleep(3)
        await self.showAction("...")


    async def upgradeFunc(self, interaction: discord.Interaction):
        if interaction.user != self.board.getCurrentPlayer().discord:
            await interaction.response.send_message("Ce n'est pas votre tour !", ephemeral=True)
            return
    
        self.can_roll_dice = True
        self.board.getCurrentPlayer().upgradeProperties()
        await self.deletePopup()
        await self.showAction("Vous avez amélioré toutes vos propriétés !")
    

    async def sellPropertiesFunc(self, interaction: discord.Interaction, values: list[int]):
        if interaction.user != self.board.getCurrentPlayer().discord:
            await interaction.response.send_message("Ce n'est pas votre tour !", ephemeral=True)
            return

        player = self.board.getCurrentPlayer()
        values = [int(value) for value in values]
        properties = [player.getPropertyByPosition(value) for value in values]
        total = self.board.sellProperties(player, properties)

        await self.deletePopup()
        await self.showAction(f"Vous avez vendu **{len(properties)}** propriété{String_tools.singular_or_plural(len(properties))} pour **{total} $** !")
        await async_sleep(3)
        await self.showAction("...")


    async def jailCardFunc(self, interaction: discord.Interaction):
        if interaction.user != self.board.getCurrentPlayer().discord:
            await interaction.response.send_message("Ce n'est pas votre tour !", ephemeral=True)
            return

        user = self.board.getCurrentPlayer()
        user.leaveJail()
        await self.deletePopup()
        await self.showAction("Vous êtes libéré de prison !")
        await async_sleep(2)

        self.enableButton("dice")
        await self.updateView()


    async def payJailFunc(self, interaction: discord.Interaction):
        if interaction.user != self.board.getCurrentPlayer().discord:
            await interaction.response.send_message("Ce n'est pas votre tour !", ephemeral=True)
            return

        player = self.board.getCurrentPlayer()
        player.leaveJail()
        player.loseMoney(CONST.JAIL_FEE)
        await self.deletePopup()
        await self.showAction(f"Vous avez payé **{CONST.JAIL_FEE} $** pour sortir de prison !")
        await async_sleep(2)
    

    async def useObject(self, interaction: discord.Interaction, object_id: int):
        player = self.board.getCurrentPlayer()
        object = player.getObjectById(object_id)
        action = player.useObject(self.board, object)

        await self.deletePopup()
        await self.showAction(action)
        await async_sleep(2)
    

    async def buyObjectFunc(self, interaction: discord.Interaction, object_id: int):
        object = self.board.getObjectById(object_id)

        if object is None:
            await interaction.response.send_message("Erreur: Cet objet n'existe pas !", ephemeral=True)
            return
    
        player = self.board.getCurrentPlayer()
        player.buyObject(object)
        await self.deletePopup()
        await self.showAction(f"Vous avez acheté **{object.name}** pour **{object.price} $ **!")
        await async_sleep(2)


    async def noFunc(self, interaction: discord.Interaction, text: str = "..."):
        if interaction.user != self.board.getCurrentPlayer().discord:
            await interaction.response.send_message("Ce n'est pas votre tour !", ephemeral=True)
            return

        await self.showAction(text)
        await self.deletePopup()
        await async_sleep(3)


    async def noJailFunc(self, interaction: discord.Interaction, _):
        if interaction.user != self.board.getCurrentPlayer().discord:
            await interaction.response.send_message("Ce n'est pas votre tour !", ephemeral=True)
            return

        self.disableButton("dice")
        self.enableButton("next")
        self.can_roll_dice = False
        self.userHasRolled = True
        await self.updateView()

        await self.deletePopup()
        await self.showAction("Vous restez en prison !")
        await async_sleep(2)


    def disableButton(self, button_id: str):
        button = self.getButtonById(button_id)

        if button != None:
            button.disabled = True


    def enableButton(self, button_id: str):
        button = self.getButtonById(button_id)

        if button != None:
            button.disabled = False


    async def updateView(self):
        await self.game_msg.edit(view=self)


    def getButtonById(self, custom_id):
        for item in self.children:
            if isinstance(item, discord.ui.Button) and item.custom_id == custom_id:
                return item
        return None
