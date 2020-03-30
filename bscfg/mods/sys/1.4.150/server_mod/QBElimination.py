# -*- coding: utf-8 -*-
import bs
import random,math
from bsElimination import Icon

def bsGetAPIVersion():
	return 4

def bsGetGames():
	return [QuantumBombElimination]

class QuantumBombElimination(bs.TeamGameActivity):

	@classmethod
	def getName(cls):
		return 'Quantum Bomb Elimination' if bs.getLanguage() != "Chinese" else u"量子炸弹淘汰赛"

	@classmethod
	def getScoreInfo(cls):
		return {'scoreName':'Survived',
				'scoreType':'milliseconds',
				'noneIsWinner':True}
	
	@classmethod
	def getDescription(cls,sessionType):
		return 'Elimination under meteriod shower!\nMade by Plasma Boson.' if bs.getLanguage() != "Chinese" else u"炸弹雨下的淘汰赛.\nPlasma Boson制作."

	# we're currently hard-coded for one map..
	@classmethod
	def getSupportedMaps(cls,sessionType):
		return ['Rampage']

	@classmethod
	def getSettings(cls,sessionType):
		settings = [("Epic Mode",{'default':False}),
						("Normal bombs",{'default':True}),
						("Frozen bombs",{'default':False}),
						("Sticky bombs",{'default':False}),
						("Impact bombs",{'default':False}),
						("LandMines",{'default':False}),
						("TNT",{'default':False}),
						("Random Gravity",{'default':False}),
						("All Sticky Bombs",{'default':False}),
						("Random Spawn Position",{'default':False}),
						("Random Scale",{'default':False}),
						("Lives Per Player",{'default':1,'minValue':1,'maxValue':12,'increment':1}),
											("Time Limit",{'choices':[('None',0),('1 Minute',60),
																	('2 Minutes',120),('5 Minutes',300),
																	('10 Minutes',600),('20 Minutes',1200)],'default':0}),
						("Respawn Times",{'choices':[('Shorter',0.25),('Short',0.5),('Normal',1.0),('Long',2.0),('Longer',4.0)],'default':1.0})]
						#("Land Mines",{'default':False})]
		if issubclass(sessionType,bs.TeamsSession):
			settings.append(("Solo Mode",{'default':False}))
			settings.append(("Balance Total Lives",{'default':False}))
			
		return settings
   
	# we support teams, free-for-all, and co-op sessions
	@classmethod
	def supportsSessionType(cls,sessionType):
		return True if (issubclass(sessionType,bs.TeamsSession)
						or issubclass(sessionType,bs.FreeForAllSession)) else False

	def __init__(self,settings):
		bs.TeamGameActivity.__init__(self,settings)
		if self.settings['Epic Mode']: self._isSlowMotion = True

		# show messages when players die since it's meaningful here
		self.announcePlayerDeaths = True
		
		try: self._soloMode = settings['Solo Mode']
		except Exception: self._soloMode = False
		self._scoreBoard = bs.ScoreBoard()

	def getInstanceDescription(self):
		return ('Last team standing wins.' if isinstance(self.getSession(),bs.TeamsSession) else 'Last one standing wins.') + '\n Made by Plasma Boson.'

	def getInstanceScoreBoardDescription(self):
		return 'last team standing wins' if isinstance(self.getSession(),bs.TeamsSession) else 'last one standing wins'

	def onTransitionIn(self):
		bs.TeamGameActivity.onTransitionIn(self, music='Epic' if self.settings['Epic Mode'] else 'Survival')
		self._startGameTime = bs.getGameTime()

	def onTeamJoin(self,team):
		team.gameData['survivalSeconds'] = None
		team.gameData['spawnOrder'] = []

	def onPlayerJoin(self, player):

		# no longer allowing mid-game joiners here... too easy to exploit
		if self.hasBegun():
			player.gameData['lives'] = 0
			player.gameData['icons'] = []
			# make sure our team has survival seconds set if they're all dead
			# (otherwise blocked new ffa players would be considered 'still alive' in score tallying)
			if self._getTotalTeamLives(player.getTeam()) == 0 and player.getTeam().gameData['survivalSeconds'] is None:
				player.getTeam().gameData['survivalSeconds'] = 0
			bs.screenMessage(bs.Lstr(resource='playerDelayedJoinText',subs=[('${PLAYER}',player.getName(full=True))]),color=(0,1,0))
			return
		
		player.gameData['lives'] = self.settings['Lives Per Player']

		if self._soloMode:
			player.gameData['icons'] = []
			player.getTeam().gameData['spawnOrder'].append(player)
			self._updateSoloMode()
		else:
			# create our icon and spawn
			player.gameData['icons'] = [Icon(player,position=(0,50),scale=0.8)]
			if player.gameData['lives'] > 0:
				self.spawnPlayer(player)

		# dont waste time doing this until begin
		if self.hasBegun():
			self._updateIcons()

	def _updateSoloMode(self):
		# for both teams, find the first player on the spawn order list with lives remaining
		# and spawn them if they're not alive
		for team in self.teams:
			# prune dead players from the spawn order
			team.gameData['spawnOrder'] = [p for p in team.gameData['spawnOrder'] if p.exists()]
			for player in team.gameData['spawnOrder']:
				if player.gameData['lives'] > 0:
					if not player.isAlive(): self.spawnPlayer(player)
					break

	def _updateIcons(self):
		# in free-for-all mode, everyone is just lined up along the bottom
		if isinstance(self.getSession(),bs.FreeForAllSession):
			count = len(self.teams)
			xOffs = 85
			x = xOffs*(count-1) * -0.5
			for i,team in enumerate(self.teams):
				if len(team.players) == 1:
					player = team.players[0]
					for icon in player.gameData['icons']:
						icon.setPositionAndScale((x,30),0.7)
						icon.updateForLives()
					x += xOffs

		# in teams mode we split up teams
		else:
			if self._soloMode:
				# first off, clear out all icons
				for player in self.players:
					player.gameData['icons'] = []
				# now for each team, cycle through our available players adding icons
				for team in self.teams:
					if team.getID() == 0:
						x = -60
						xOffs = -78
					else:
						x = 60
						xOffs = 78
					isFirst = True
					testLives = 1
					while True:
						playersWithLives = [p for p in team.gameData['spawnOrder'] if p.exists() and p.gameData['lives'] >= testLives]
						if len(playersWithLives) == 0: break
						for player in playersWithLives:
							player.gameData['icons'].append(Icon(player,
																 position=(x,(40 if isFirst else 25)),
																 scale=1.0 if isFirst else 0.5,
																 nameMaxWidth=130 if isFirst else 75,
																 nameScale=0.8 if isFirst else 1.0,
																 flatness=0.0 if isFirst else 1.0,
																 shadow=0.5 if isFirst else 1.0,
																 showDeath=True if isFirst else False,
																 showLives=False))
							x += xOffs * (0.8 if isFirst else 0.56)
							isFirst = False
						testLives += 1
			# non-solo mode
			else:
				for team in self.teams:
					if team.getID() == 0:
						x = -50
						xOffs = -85
					else:
						x = 50
						xOffs = 85
					for player in team.players:
						for icon in player.gameData['icons']:
							icon.setPositionAndScale((x,30),0.7)
							icon.updateForLives()
						x += xOffs
					
	def _getSpawnPoint(self,player):
		# in solo-mode, if there's an existing live player on the map, spawn at whichever
		# spot is farthest from them (keeps the action spread out)
		if self._soloMode:
			livingPlayer = None
			for team in self.teams:
				for player in team.players:
					if player.isAlive():
						p = player.actor.node.position
						livingPlayer = player
						livingPlayerPos = p
						break
			if livingPlayer:
				playerPos = bs.Vector(*livingPlayerPos)
				points = []
				for team in self.teams:
					startPos = bs.Vector(*self.getMap().getStartPosition(team.getID()))
					points.append([(startPos-playerPos).length(),startPos])
				points.sort()
				return points[-1][1]
			else:
				return None
		else:
			return None

		
	def spawnPlayer(self,player):
		
		self.spawnPlayerSpaz(player,self._getSpawnPoint(player))
		if not self._soloMode:
			bs.gameTimer(300,bs.Call(self._printLives,player))

		# if we have any icons, update their state
		for icon in player.gameData['icons']:
			icon.handlePlayerSpawned()

	def _printLives(self,player):
		if not player.exists() or not player.isAlive(): return
		try: pos = player.actor.node.position
		except Exception,e:
			print 'EXC getting player pos in bsElim',e
			return
		bs.PopupText('x'+str(player.gameData['lives']-1),color=(1,1,0,1),
						   offset=(0,-0.8,0),randomOffset=0.0,scale=1.8,position=pos).autoRetain()

	def onPlayerLeave(self,player):

		bs.TeamGameActivity.onPlayerLeave(self,player)

		player.gameData['icons'] = None

		# remove us from spawn-order
		if self._soloMode:
			if player in player.getTeam().gameData['spawnOrder']:
				player.getTeam().gameData['spawnOrder'].remove(player)

		# update icons in a moment since our team will be gone from the list then
		bs.gameTimer(0, self._updateIcons)

	def onBegin(self):
		bs.TeamGameActivity.onBegin(self)
		self.setupStandardTimeLimit(self.settings['Time Limit'])
		self.setupStandardPowerupDrops()

		if self._soloMode:
			self._vsText = bs.NodeActor(bs.newNode("text",
												   attrs={'position':(0,105),
														  'hAttach':"center",
														  'hAlign':'center',
														  'maxWidth':200,
														  'shadow':0.5,
														  'vrDepth':390,
														  'scale':0.6,
														  'vAttach':"bottom",
														  'color':(0.8,0.8,0.3,1.0),
														  'text':bs.Lstr(resource='vsText')}))

		# if balance-team-lives is on, add lives to the smaller team until total lives match
		if (isinstance(self.getSession(),bs.TeamsSession)
			and self.settings['Balance Total Lives']
			and len(self.teams[0].players) > 0
			and len(self.teams[1].players) > 0):
			if self._getTotalTeamLives(self.teams[0]) < self._getTotalTeamLives(self.teams[1]):
				lesserTeam = self.teams[0]
				greaterTeam = self.teams[1]
			else:
				lesserTeam = self.teams[1]
				greaterTeam = self.teams[0]
			addIndex = 0
			while self._getTotalTeamLives(lesserTeam) < self._getTotalTeamLives(greaterTeam):
				lesserTeam.players[addIndex].gameData['lives'] += 1
				addIndex = (addIndex + 1) % len(lesserTeam.players)

		self._updateIcons()

		# we could check game-over conditions at explicit trigger points,
		# but lets just do the simple thing and poll it...
		bs.gameTimer(1000, self._update, repeat=True)
		
		# drop a wave every few seconds.. and every so often drop the time between waves
		# ..lets have things increase faster if we have fewer players
		self._meteorTime = 10000
		t = 5000 if len(self.players) > 2 else 2500
		if self.settings['Epic Mode']: t /= 2
		bs.gameTimer(t,self._decrementMeteorTime,repeat=True)

		# kick off the first wave in a few seconds
		t = 4000
		if self.settings['Epic Mode']: t /= 2
		bs.gameTimer(t,self._setMeteorTimer)

		self._timer = bs.OnScreenTimer()
		bs.gameTimer(t,self._timer.start)
		
		
	# overriding the default character spawning..
	def spawnPlayer(self,player):
		
		self.spawnPlayerSpaz(player,self._getSpawnPoint(player))
		if not self._soloMode:
			bs.gameTimer(300,bs.Call(self._printLives,player))

		# if we have any icons, update their state
		for icon in player.gameData['icons']:
			icon.handlePlayerSpawned()

	# various high-level game events come through this method
	def handleMessage(self,m):

		if isinstance(m,bs.PlayerSpazDeathMessage):
			
			bs.TeamGameActivity.handleMessage(self, m) # augment standard behavior
			player = m.spaz.getPlayer()

			player.gameData['lives'] -= 1
			if player.gameData['lives'] < 0:
				bs.printError('Got lives < 0 in Elim; this shouldnt happen. solo:'+str(self._soloMode))
				player.gameData['lives'] = 0

			# if we have any icons, update their state
			for icon in player.gameData['icons']:
				icon.handlePlayerDied()

			# play big death sound on our last death or for every one in solo mode
			if self._soloMode or player.gameData['lives'] == 0:
				bs.playSound(bs.Spaz.getFactory().singlePlayerDeathSound)

			# if we hit zero lives, we're dead (and our team might be too)
			if player.gameData['lives'] == 0:
				# if the whole team is now dead, mark their survival time..
				#if all(teammate.gameData['lives'] == 0 for teammate in player.getTeam().players):
				if self._getTotalTeamLives(player.getTeam()) == 0:
					player.getTeam().gameData['survivalSeconds'] = (bs.getGameTime()-self._startGameTime)/1000
			else:
				# otherwise, in regular mode, respawn..
				if not self._soloMode:
					self.respawnPlayer(player)

			# in solo, put ourself at the back of the spawn order
			if self._soloMode:
				player.getTeam().gameData['spawnOrder'].remove(player)
				player.getTeam().gameData['spawnOrder'].append(player)
	def _getTotalTeamLives(self,team):
		return sum(player.gameData['lives'] for player in team.players)
	def _checkEndGame(self):
		livingTeamCount = 0
		for team in self.teams:
			for player in team.players:
				if player.isAlive():
					livingTeamCount += 1
					break

		# in co-op, we go till everyone is dead.. otherwise we go until one team remains
		if isinstance(self.getSession(),bs.CoopSession):
			if livingTeamCount <= 0: self.endGame()
		else:
			if livingTeamCount <= 1: self.endGame()
		
	def _setMeteorTimer(self):
		bs.gameTimer(int((1.0+0.2*random.random())*self._meteorTime),self._dropBombCluster)     

	def _dropBombCluster(self):

		# random note: code like this is a handy way to plot out extents and debug things
		if False:
			bs.newNode('locator',attrs={'position':(8,6,-5.5)})
			bs.newNode('locator',attrs={'position':(8,6,-2.3)})
			bs.newNode('locator',attrs={'position':(-7.3,6,-5.5)})
			bs.newNode('locator',attrs={'position':(-7.3,6,-2.3)})

		# drop several bombs in series..
		
		delay = 0
		types = []
		if self.settings['Normal bombs']:
			types.append("normal")
		 
		if self.settings['Frozen bombs']:
			types.append("ice")

		if self.settings['Sticky bombs']:
			types.append("sticky")

		if self.settings['Impact bombs']:
			types.append("impact")

		if self.settings['TNT']:
			types.append("tnt")

		if self.settings['LandMines']:
			types.append("landMine")
		
		if types == []:types.append("normal")
		
		sticky = self.settings['All Sticky Bombs']
		
		for i in range(random.randrange(1,5)):
			
			# drop them somewhere within our bounds with velocity pointing toward the opposite side
			Vy = -4.0
			map = self.getMap().getName()
			if map == 'Happy Thoughts': 
					 pos = (-20+40*random.random(),22,0+0*random.random())                  
			elif map=='Doom Shroom':
				 pos = (-10+20*random.random(),8,-10+15*random.random())
			elif map=='Monkey Face':
				 pos = (-9.6+15*random.random(),9,-11+16.5*random.random())
			elif map=='Big G':
				 pos = (-10+18*random.random(),10,-11+18*random.random())
			elif map=='Bridgit':
				 pos = (-8+15*random.random(),8,-4+4.5*random.random())
			elif map=='Courtyard':
				 pos = (-10+20*random.random(),8,-11+15*random.random())
			elif map=='Crag Castle':
				 pos = (-8+16.2*random.random(),12,-7+10*random.random())
			elif map=='Football Stadium':
				 pos = (-15+30*random.random(),10,-7+13*random.random())
			elif map=='Hockey Stadium':
				 pos = (-15+30*random.random(),6.85,-7+13*random.random())
			elif map=='Rampage':
				 pos = (-7.3+15.3*random.random(),11,-5.5+2.1*random.random())
			elif map=='Roundabout':
				 pos = (-7.3+12*random.random(),11,-7+7.5*random.random())
			elif map=='Step Right Up':
				 pos = (-8+21*random.random(),11,-9+12*random.random())
			elif map=='The Pad':
				 pos = (-8+16*random.random(),11,-10+14*random.random())
			

			
			
			gav = random.uniform(-3,3) if self.settings['Random Gravity'] else None
			
			if gav < 0:Vy = random.uniform(-10,10)
			
			scale = random.uniform(0,4) if self.settings['Random Scale'] else None
			
			
			
			bt = random.choice(types)
			if self.settings['Random Spawn Position']:
				pos = bs.getActivity().getMap().getFFAStartPosition(bs.getSession().players)
				pos = list(pos)
				pos = (pos[0],pos[1]+0.6,pos[2])
				vel = (random.uniform(-1,1)*math.log(random.uniform(0,1024),2),0,random.uniform(-1,1)*math.log(random.uniform(0,1024),2))
				gav = 0.0
			else:vel = ((-5.0+random.random()*30.0) * (-1.0 if pos[0] > 0 else 1.0), Vy,0)
			bs.gameTimer(delay,bs.Call(self._dropBomb,pos,vel,bt,sticky,gav,scale))
			delay += 100
		self._setMeteorTimer()

	def _dropBomb(self,position,velocity,bombType,sticky = False,gravity = None , scale = None):
		b = bs.Bomb(position=position,velocity=velocity,bombType=bombType,blastRadius=2.0 if scale is None else 2.0*scale).autoRetain()
		if bombType in ["landMine"]:b.arm()
		if sticky:b.node.sticky = True
		if gravity is not None:b.node.gravityScale = gravity
		if scale is not None:
			def _safeAnimate(node,attr,val):
				if node.exists(): bs.animate(node,attr,val)
			bs.gameTimer(260,bs.Call(_safeAnimate,b.node,"modelScale",{0:1,300:scale}))
	def _decrementMeteorTime(self):
		self._meteorTime = max(100,int(self._meteorTime*0.9))

	def _update(self):

		if self._soloMode:
			# for both teams, find the first player on the spawn order list with lives remaining
			# and spawn them if they're not alive
			for team in self.teams:
				# prune dead players from the spawn order
				team.gameData['spawnOrder'] = [p for p in team.gameData['spawnOrder'] if p.exists()]
				for player in team.gameData['spawnOrder']:
					if player.gameData['lives'] > 0:
						if not player.isAlive():
							self.spawnPlayer(player)
							self._updateIcons()
						break
		
		# if we're down to 1 or fewer living teams, start a timer to end the game
		# (allows the dust to settle and draws to occur if deaths are close enough)
		if len(self._getLivingTeams()) < 2:
			self._roundEndTimer = bs.Timer(500,self.endGame)


	def _getLivingTeams(self):
		return [team for team in self.teams if len(team.players) > 0 and any(player.gameData['lives'] > 0 for player in team.players)]

	def endGame(self):
		if self.hasEnded(): return
		results = bs.TeamGameResults()
		self._vsText = None # kill our 'vs' if its there
		for team in self.teams:
			results.setTeamScore(team, team.gameData['survivalSeconds'])#;print team.gameData['survivalSeconds']
		self.end(results=results)
		
