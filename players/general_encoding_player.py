# -*- coding: utf-8 -*-
"""
Created on Sun May 08 12:57:34 2016

@author: robieta
"""

from copy import deepcopy as c
import itertools as it
import numpy as np
import random, re, sys, time
from hanabi_classes import AIPlayer

class GeneralEncodingPlayer(AIPlayer):

    @classmethod
    def get_name(cls):
        return 'gencoder'

    def __init__(self, me, logger, verbosity):
        super(GeneralEncodingPlayer, self).__init__(me, logger, verbosity)
        # This boolean is for replicate runs. Certain initialization routines
        # only need to be performed once, and can be carried over across
        # multiple games. However since the initialization depends on the game
        # specifics, the __init__ function only tracks whether it has taken
        # place.
        self.Initialized = False                  
 
    def play(self,r):
        r.HandHistory.append(c(r.h))
        nPriorTurns = len(r.playHistory)
        if nPriorTurns <= r.nPlayers - 1:
            self.Startup(r)
            
        self.GenerateHandRecord(r)       
        self.UpdateInfoMat(r)

        PlayableCards, ExpectedValue = self.GetPlayableIndex(r)
        DiscardableCards, SaferDiscard, AlreadyPlayed = self.GetDiscardable(r)
        
        # If PrintInternal is set to true, internal state information will be 
        # printed. Recommended to be used with verbose output. The sleep call
        # is to ensure prints are grouped with the correct verbose log print.
        # It does, however, slow down evaluation somewhat.
        PrintInternal = False
        if PrintInternal:
            if nPriorTurns == 0:
                print('\n'*10)
            
            print('')
            self.PrintInfoMat(self.SelfID)
            print(r.progress)
            time.sleep(0.4)
         
        
        """Central Strategy Block"""
        # This block is intended to compactly specify the AI strategy so that
        # one need not necessarily learn the entire code framework in order to
        # experiment with different strategies
        # ---------------------------------------------------------------------
        
        # If the game is already won, there is no need to play anything
        # (also it messes up the set theory code)
        if (np.sum([r.progress[key] for key in r.progress]) 
            == 5*len(self.SuitSet)):
            return 'discard',r.h[r.whoseTurn].cards[0]
        
        
        SemiSafeCutoff = 0.85
        if len(DiscardableCards) > 0 and r.lightning < 2:
            pPlayable = self.GetSemiSafePlay(r,SaferDiscard)    
            if np.max(pPlayable) >= SemiSafeCutoff:
                PlayIndex = ([m for m,M in enumerate(pPlayable) 
                            if M == np.max(pPlayable)][0])
                return 'play',r.h[r.whoseTurn].cards[PlayIndex]
        

        # Play the card with the lowest expected value
        if len(PlayableCards) > 0:
            PlayIndex = [M for m,M in enumerate(PlayableCards) if 
                        ExpectedValue[m] == np.min(ExpectedValue)][0]
            return 'play',r.h[r.whoseTurn].cards[PlayIndex]
            
        
        nPlayed = self.GetnPlayed(r)
        NearEndCutoff = 2
        
        # Estimate for the number of cards left to be drawn. Incorrect in the
        # end game (incomplete hands) but that is fine
        nDraw = len(self.SortedDeck)  - nPlayed - self.nPlayers * self.nCards
        
        # Preempt normal discard to use up hints, drag out game.
        if nDraw <= NearEndCutoff and r.hints > 0:
            Code = self.GenerateCode(nPriorTurns,self.SelfID,
                                 self.GroupCardNumbers(r.progress),r.progress)
            Hint = self.DetermineHint(Code,self.SelfID,nPriorTurns)
            return 'hint', (Hint[0],Hint[1])
        
        # Again, the choice of which card to discard is very primitive (lowest
        # index, favoring cards that have already been played)
        if len(DiscardableCards) > 0 and r.hints < self.nPlayers-1:
            if len(AlreadyPlayed) > 0:
                DiscardIndex = AlreadyPlayed[0]
            elif len(SaferDiscard) > 0:
                DiscardIndex = SaferDiscard[0]
            else:
                DiscardIndex = DiscardableCards[0]
            return 'discard',r.h[r.whoseTurn].cards[DiscardIndex]
            
        if r.hints == 0:
#            self.PrintInfoMat()
#            return 'resign', ''
            return 'discard',r.h[r.whoseTurn].cards[0]
            
        Code = self.GenerateCode(nPriorTurns,self.SelfID,
                                 self.GroupCardNumbers(r.progress),r.progress)
        Hint = self.DetermineHint(Code,self.SelfID,nPriorTurns)
        return 'hint', (Hint[0],Hint[1])
        # ---------------------------------------------------------------------

            
    def InitializeConstants(self,r):
        """ Monte Carlo Constants"""
        # The combinatorics are such that complete enumeration is impractical.
        # Instead, combinations are psudo randomly selected and tested. Larger
        # sampling will produce better results at the cost of longer run times
        self.nMCCandidates = np.float(1e2)
    
    
        # This block initializes constants which depend on game specifics         
        self.nPlayers = r.nPlayers
        self.nCards = len(r.h[r.whoseTurn].cards)
        
        if not self.Initialized:
            self.Initialized = True
            self.StaticCombinatorics()
        
        self.SelfID = r.whoseTurn
        self.OtherIDs = [i for i in range(r.nPlayers) if i != self.SelfID]
        
        self.SuitSet = ['r','y','g','b','w']
        self.NumberSet = [str(i+1) for i in range(5)]
        
        self.SortedDeck = []
        for suit in self.SuitSet:
            for number in '1112233445':
                self.SortedDeck.append(number + suit)
        
        # I choose to represent the information matrix as a dictionary because
        # it makes it easier to retreive elements. The tradeoff is that the 
        # intrinsic structure is not contained in the variable. However, the
        # shape is always nPlayers x nCards, so this is acceptable
        self.InformationMatrix = {}
        for i in range(self.nPlayers):
            # "Dummy" r1 at the -1 position can be pointed to during encoding
            # if the origional target is not present (less than full hand size)
            # See self.GenerateHandRecord for more information
            self.InformationMatrix[i,-1,'S'] = ['r']
            self.InformationMatrix[i,-1,'N'] = [1]
            for j in range(self.nCards):
                self.InformationMatrix[i,j,'S'] = c(self.SuitSet)
                self.InformationMatrix[i,j,'N'] = c(self.NumberSet)

        # I plan on using random sampling methods to study different play
        # strategies. However, introduction of a full CSPRNG would 
        # desynchronize the players. Instead, I use a shared fixed seed so all
        # players can access the same list of psudo random numbers.                
        self.StartRandom(r.CommonSeed)
        self.RandomSeedList = [random.randint(1,sys.maxint) for i in 
                               range(100)]
        self.EndRandom()
        
        # added to avoid "magic numbers"
        self.MaxCardNumber = np.max([int(i) for i in self.NumberSet])
        
        # The encoding AI considers transmitting encoded subsets to more
        # efficiently satisfy the integer constrained nature of bits        
        if self.nPlayers == 2:
            self.NumSetCombo = [[2,5],[3,3]]
        elif self.nPlayers == 3:
            self.NumSetCombo =[[2,2,5],[4,5],[2,3,3]]
        elif self.nPlayers == 4:
            self.NumSetCombo = [[2,3,5],[3,3,3],[5,5],[2,2,2,3]]
        elif self.nPlayers == 5:
            self.NumSetCombo = [[2,2,2,5],[2,4,5],[2,2,3,3],[3,3,4],
                                [2,2,2,2,2],[5,5]]
        else:
            raise NameError('Invalid number of players for this AI')
            
        # Misc. Values
        self.RunningPlayInd = -1
        
    def GetnPlayed(self,r):
        nPlayed = 0
        for I in r.playHistory:
            if I[0] == 'play' or I[0] == 'discard':
                nPlayed += 1
        return nPlayed

    def GetCountFromDiscard(self,r,turn = ''):
        # Card counting function, uses the played and discarded cards
        if turn == '':
            turn = len(r.playHistory)
        CardCount = {i:0 for i in np.unique(self.SortedDeck)}
        for i in self.SortedDeck:
            CardCount[i] += 1
        for i,I in enumerate(r.playHistory[:turn]):
            if I[0] == 'play' or I[0] == 'discard':
                CardCount[I[1]['name']] -= 1
            elif I[0] == 'hint':
                pass
            else:
                raise NameError('')
        return CardCount
        
    def GetCardCountFromHandAndDiscard(self,r):
        # Card counting function. Uses played, discarded, and other players'
        # hands.
        CardCount = self.GetCountFromDiscard(r)
        for i in self.OtherIDs:
            for j in range(self.nCards):
                Value = self.HandHistory[-1][i,j]
                if Value != 'xx':
                    CardCount[Value] -= 1
        return CardCount
        
    def GetSemiSafePlay(self,r,SafeDiscard):
        # This function calculates the probability that a card is safe to play.
        # It only does this for the cards that are safe to discard. That way
        # the game isn't ruined if it plays an invalid card.
        progress = r.progress
        CardCount = self.GetCardCountFromHandAndDiscard(r)
        PlayableSet = [str(progress[key]+1) + key for key in progress]
        pPlayable = [0 for m in range(self.nCards)]
        for i in SafeDiscard:
            N = self.InformationMatrix[self.SelfID,i,'N']
            S = self.InformationMatrix[self.SelfID,i,'S']
            PossibleSet = [m[0] + m[1] for m in list(it.product(N,S))]
            PosPlayable = [1 if m in PlayableSet else 0 for m in PossibleSet]
            PosCount = [CardCount[m] for m in PossibleSet]
            pPlayable[i] =  (np.float(np.sum(np.array(PosCount)*
                            np.array(PosPlayable)))/np.sum(PosCount))
        return pPlayable    
            
    def GetPlayableIndex(self,r):
        # Gets which cards in the player's hand are safely playable.
        progress = r.progress
        CardCount = self.GetCardCountFromHandAndDiscard(r)
        PlayableSet = [str(progress[key]+1) + key for key in progress]
        nSuits = len(PlayableSet)
        PlayableCards = []
        ExpectedValue = []
        for i in range(self.nCards):
            N = self.InformationMatrix[self.SelfID,i,'N']
            S = self.InformationMatrix[self.SelfID,i,'S']
            PossibleSet = [m[0] + m[1] for m in list(it.product(N,S))]
            nPos = len(PossibleSet)
            Playable = False
            if nPos <= nSuits:
                if len(set(PossibleSet).intersection(PlayableSet)) == nPos:
                    Playable = True
            if Playable:
                PlayableCards.append(i)
                PosSetCount = [CardCount[m] for m in PossibleSet]
                PosSetVal = [int(m[0]) for m in PossibleSet]
                ExpectedValue.append(
                    float(np.sum(np.array(PosSetCount)*np.array(PosSetVal)))
                    /np.sum(PosSetCount))
        return PlayableCards, ExpectedValue
        
    def GetDiscardable(self,r):
        # Gets which cards can be discarded:
        # SafeDiscard = can be discarded
        # SaferDiscard = more than 1 other copy
        # SafestDiscard = already played, no issue with discarding
        SafeDiscard = []
        SaferDiscard = []
        SafestDiscard = []
        CardCount = self.GetCountFromDiscard(r)
        
        for i in range(self.nCards):
            N = self.InformationMatrix[self.SelfID,i,'N']
            S = self.InformationMatrix[self.SelfID,i,'S']
            PossibleSet = [m[0] + m[1] for m in list(it.product(N,S))]            
            AlreadyPlayed = [1 if int(m[0]) <= r.progress[m[1]] 
                             else 0 for m in PossibleSet]
            MultipleLeft = [1 if CardCount[m] > 1 else 0 for m in PossibleSet]
            MultipleLeft2 = [1 if CardCount[m] > 2 else 0 for m in PossibleSet]
            SafeDiscardBool =   np.min([1 if AlreadyPlayed[m] == 1 or 
                                MultipleLeft[m] == 1 else 0 for m in 
                                range(len(PossibleSet))]) == 1
            if SafeDiscardBool:
                SafeDiscard.append(i)
            if np.min(MultipleLeft2) == 1:
                SaferDiscard.append(i)
            if np.min(AlreadyPlayed) == 1:
                SafestDiscard.append(i)
        return SafeDiscard, SaferDiscard, SafestDiscard
            
    def GenerateHandRecord(self,r):
        # Converts the hands in r into a form used in this algorithm. This has
        # several functions:
        # 1) More convenient to access
        # 2) No cheating. One's own hands are aliased as 'xx'
        # 3) Builds an 'InPlay' list which allows exclusion of cards from 
        #    encoding
        self.HandHistory = []
        self.DirectRecord = []
        self.IndirectRecord = []
        self.InPlay = []
        for i in r.HandHistory:
            self.HandHistory.append({})
            self.DirectRecord.append({})
            self.IndirectRecord.append({})
            self.InPlay.append({})
            for j in range(self.nPlayers):
                # This line is somewhat unintuitive. Each player is assigned a
                # psudo card within the framework of of the internal 
                # information accounting. Moreover, the value of this psudo
                # card is considered to be know. For this reason, if a code
                # ever points to a card which should not be considered (either
                # because a player has less than a full hand and the card does
                # not exist or because that player has spent its last turn and
                # revealing its cards would serve no purpose except to skew the
                # code generation) then it can be redirected to the '-1' index
                # as a dummy card.
                self.HandHistory[-1][j,-1] = '1r'
                for k in range(self.nCards):
                    if k < len(i[j].cards):
                        self.DirectRecord[-1][j,k] = ([str(m) for m in 
                                                    i[j].cards[k]['direct']])
                        self.IndirectRecord[-1][j,k] = ([str(m) for m in 
                                                    i[j].cards[k]['indirect']])
                        self.InPlay[-1][j,k] = True
                        if j == self.SelfID:
                            # This prevents players from looking at their own 
                            # hands
                            self.HandHistory[-1][j,k] = 'xx'
                        else:
                            self.HandHistory[-1][j,k] = i[j].cards[k]['name']
                    else:
                        self.DirectRecord[-1][j,k] = []
                        self.IndirectRecord[-1][j,k] = []
                        self.HandHistory[-1][j,k] = 'xx'
                        self.InPlay[-1][j,k] = False
        
        self.HandHistory.append({})
        self.DirectRecord.append({})
        self.IndirectRecord.append({})
        self.InPlay.append({})
        for j in range(self.nPlayers):
            self.HandHistory[-1][j,-1] = '1r'
            for k in range(self.nCards):
                if k < len(r.h[j].cards):
                    self.DirectRecord[-1][j,k] = ([str(m) for m in 
                                                r.h[j].cards[k]['direct']])
                    self.IndirectRecord[-1][j,k] = ([str(m) for m in 
                                                r.h[j].cards[k]['indirect']])
                    self.InPlay[-1][j,k] = True
                    if j == self.SelfID:
                        # This prevents players from looking at their own hands
                        self.HandHistory[-1][j,k] = 'xx'
                    else:
                        self.HandHistory[-1][j,k] = r.h[j].cards[k]['name']
                else:
                    self.DirectRecord[-1][j,k] = []
                    self.IndirectRecord[-1][j,k] = []
                    self.HandHistory[-1][j,k] = 'xx'
                    self.InPlay[-1][j,k] = False
            
    def UpdateInfoMat(self,r):
        # This is the heart of the encoding scheme. It takes the hints that 
        # have been given and inverts the encoding to determine what has been
        # transmitted.
        CurrentTurn = len(r.playHistory)
        if CurrentTurn > 0:
            FirstEvalTurn = np.max([CurrentTurn - self.nPlayers,0])
            TurnEvalRange = range(FirstEvalTurn,CurrentTurn)
            for Turn in TurnEvalRange:
                PlayType = r.playHistory[Turn][0]
                CurrentPlayer = Turn % self.nPlayers
                if PlayType == 'hint':
                    HintingPlayer = CurrentPlayer
                    
                    # Back out the dynamic code chosen by the hinting player
                    Code = self.GenerateCode(Turn,HintingPlayer,
                                self.GroupCardNumbers(r.progressHistory[Turn]),
                                r.progressHistory[Turn])
                    self.UpdateInformationMatrix(r.playHistory[Turn][1],Code,
                         HintingPlayer,Turn)
                    for i in range(self.nPlayers):
                        for j in range(self.nCards):
                            # Use the actual hinted information in addition to
                            # the encoded information
                            for k in self.DirectRecord[Turn][i,j]:
                                if k in self.NumberSet:
                                    self.InformationMatrix[i,j,'N'] = k
                                else:
                                    self.InformationMatrix[i,j,'S'] = k
                            self.InformationMatrix[i,j,'N'] = list(set(
                                self.InformationMatrix[i,j,'N']).difference(
                                self.IndirectRecord[Turn][i,j]))
                            self.InformationMatrix[i,j,'S'] = list(set(
                                self.InformationMatrix[i,j,'S']).difference(
                                self.IndirectRecord[Turn][i,j]))
                                
                            # Use card counting methods to further restrict
                            # possibilities.
                            Improvement = True
                            while Improvement:
                                Improvement = self.CardCountInfoMat(r,Turn)
                elif PlayType == 'play' or PlayType == 'discard':
                    # Shift cards to the left and initialize the rightmost
                    # card as unknown: [1,2,3,4,5]['r','y','g','b','w']
                    # If there is no card (endgame) this initialization is
                    # incorrect; however anything that points to that slot gets
                    # redirected to the dummy r1 at the -1 position.
                    self.RunningPlayInd += 1  
                    DroppedCardInd = r.DropIndRecord[self.RunningPlayInd]
                    for j in range(DroppedCardInd,self.nCards-1):
                        self.InformationMatrix[CurrentPlayer,j,'N'] = c(
                                self.InformationMatrix[CurrentPlayer,j+1,'N'])
                        self.InformationMatrix[CurrentPlayer,j,'S'] = c(
                                self.InformationMatrix[CurrentPlayer,j+1,'S'])
                    self.InformationMatrix[CurrentPlayer,self.nCards-1,'N'] = (
                            c(self.NumberSet))
                    self.InformationMatrix[CurrentPlayer,self.nCards-1,'S'] = (
                            c(self.SuitSet))
                else:
                    raise NameError('Still to be implemented')
        # Raise exception if a mistake is made
        self.CheckInfoMat(r)
    
    def CardCountInfoMat(self,r,Turn):
        # This function uses card counting methods to restrict the 
        # possibilities of the information matrix
        Improvement = False
        CardCount = self.GetCountFromDiscard(r,Turn)
        for i in range(self.nPlayers):
            for j in range(self.nCards):
                if (len(self.InformationMatrix[i,j,'N']) == 1 and
                    len(self.InformationMatrix[i,j,'S']) == 1):
                        CardVal = (self.InformationMatrix[i,j,'N'][0]
                                    + self.InformationMatrix[i,j,'S'][0])
                        CardCount[CardVal] -= 1
        
        for i in range(self.nPlayers):
            for j in range(self.nCards):
                N = self.InformationMatrix[i,j,'N']
                S = self.InformationMatrix[i,j,'S']
                if len(N) > 1 or len(S) > 1:
                    PossibleSet = ([m[0] + m[1] for m in 
                        list(it.product(N,S)) if 
                        CardCount[m[0] + m[1]] > 0])
                    Nnew = np.unique([m[0] for m in PossibleSet]).tolist()
                    Snew = np.unique([m[1] for m in PossibleSet]).tolist()
                    if len(Nnew) < len(N) or len(Snew) < len(S):
                        Improvement = True
                        self.InformationMatrix[i,j,'N'] = c(Nnew)
                        self.InformationMatrix[i,j,'S'] = c(Snew)

            return Improvement
    
    def CheckInfoMat(self,r):
        # Check to see if the information matrix is wrong, and if so raise an
        # exception.
        for i in range(self.nPlayers):
            for j in range(self.nCards):
                if j < len(r.h[i].cards):
                    N = self.InformationMatrix[i,j,'N']
                    S = self.InformationMatrix[i,j,'S']
                    PossibleSet = [m[0] + m[1] for m in list(it.product(N,S))]
                    if r.h[i].cards[j]['name'] not in PossibleSet:
                        print(r.playHistory)
                        print(r.DropIndRecord)
                        for m in range(self.nCards):
                            print(self.InformationMatrix[i,m,'N'],)
                            print(self.InformationMatrix[i,m,'S'],)
                            print(' ' * 10,)
                        print('')
                        for m in range(self.nCards):
                            print(r.h[i].cards[m]['name'],)
                            print(' ' * 10,)
                        print('')
                        raise NameError('Error detected in the information matrix')
            
    def ExpandCode(self,Code):
        # Utility function, just converts a string into several lists
        CodeList = Code.split('__')
        TypeList = [i.split('_')[0] for i in CodeList]
        ColList = [i.split('_')[1] for i in CodeList]
        GroupSetList = [i.split('_')[2] for i in CodeList]
        EvalSetList = [[['r'],['y'],['g'],['b'],['w']] if i == 
                    '[[r],[y],[g],[b],[w]]' else eval(i) for i in GroupSetList]
        EncodeBase = [len(i) for i in EvalSetList]
        PossibleResultList = list(it.product(*[range(i) for i in EncodeBase]))
        return (CodeList,TypeList,ColList,GroupSetList,EvalSetList,EncodeBase,
                PossibleResultList)
    
    def UpdateInformationMatrix(self,Hint,Code,HintingPlayer,Turn):
        # This is the function which performs the modular arithmetic back
        # calculation to convert a code and hint into the underlying encoded
        # information and transfers it into the information matrix.
        ActualResult = self.BackCalcHintedState(Hint,Code,HintingPlayer)
        (CodeList,TypeList,ColList,GroupSetList,EvalSetList,EncodeBase,
             PossibleResultList) = self.ExpandCode(Code)
        NonHintingIDs = [m for m in range(self.nPlayers) if m != HintingPlayer]
        OtherNonHintingIDs = [m for m in NonHintingIDs if m != self.SelfID]
        CodePosOtherNonHinting = [m for m,M in enumerate(NonHintingIDs) if M != self.SelfID]
        for i,I in enumerate(CodeList):
            CurrentColList = [int(m) for m in ColList[i].split(',')]
            CurrentOtherColList = [CurrentColList[m] for m in CodePosOtherNonHinting]
            OtherHandVals = []
            for j,J in enumerate(OtherNonHintingIDs):
                # Within this loop "Val" refers to the index of the set which
                # the card is known to belong
                HandValue = self.HandHistory[Turn][J,CurrentOtherColList[j]]
                if TypeList[i] == 'S':
                    HandValue = HandValue[-1]
                else:
                    HandValue = int(HandValue[:-1])
                OtherHandVals.append(
                 [m for m,M in enumerate(EvalSetList[i]) if HandValue in M][0])
            if self.SelfID != HintingPlayer:
                SelfVal = int((ActualResult[i] - np.sum(OtherHandVals)) 
                            % len(EvalSetList[i]))
            OtherHandValsRev = c(OtherHandVals)
            OtherHandValsRev.reverse()
            NonHintingVals = ([OtherHandValsRev.pop() if M != self.SelfID 
                                else SelfVal for M in NonHintingIDs])
            for j,J in enumerate(NonHintingIDs):
                RestrictedSet = EvalSetList[i][NonHintingVals[j]]
                RestrictedSet = [str(m) for m in RestrictedSet]
                self.InformationMatrix[J,CurrentColList[j],TypeList[i]] = (
                    list(set(self.InformationMatrix[J,CurrentColList[j],
                    TypeList[i]]).intersection(RestrictedSet)))
            
    def BackCalcHintedState(self,Hint,Code,HintingPlayer):
        # Converts the actual hint (i.e. player 3 green) into the intended
        # vector of numbers (i.e. [2,0,0])
        OtherIDs = [m for m in range(self.nPlayers) if m != HintingPlayer]
        (CodeList,TypeList,ColList,GroupSetList,EvalSetList,EncodeBase,
             PossibleResultList) = self.ExpandCode(Code)
        NumSuitSet = c(self.NumberSet)
        [NumSuitSet.append(m) for m in self.SuitSet]
        ResultSelection = ([m for m,M in enumerate(list(
                            it.product(OtherIDs,NumSuitSet))) 
                            if np.array_equal(M,Hint)][0])
        ActualResult = PossibleResultList[ResultSelection]
        return ActualResult
        
    def DetermineHint(self,Code,HintingPlayer,Turn):
        # Takes a selected code, looks at the other players' hands, and
        # determines what hint to give to provide the information corresponding
        # to the selected code.
        OtherIDs = [m for m in range(self.nPlayers) if m != HintingPlayer]
        (CodeList,TypeList,ColList,GroupSetList,EvalSetList,EncodeBase,
             PossibleResultList) = self.ExpandCode(Code)
        ActualResult = []
        for i,I in enumerate(CodeList):
            Columns = [int(m) for m in ColList[i].split(',')]
            PositionInSetList = []
            for j,J in enumerate(Columns):
                RawVal = (self.HandHistory[Turn][OtherIDs[j],J]
                            [0 if TypeList[i] == 'N' else 1])
                if TypeList[i] == 'N':
                    RawVal = int(RawVal)
                PositionInSetList.append([m for m,M in enumerate(EvalSetList[i]) 
                                    if RawVal in M][0])
            ActualResult.append(
                np.sum(PositionInSetList) % len(EvalSetList[i]))
        ResultSelection = ([m for m,M in enumerate(PossibleResultList) 
                            if np.array_equal(M,ActualResult)][0])
                                
        NumSuitSet = c(self.NumberSet)
        [NumSuitSet.append(m) for m in self.SuitSet]
        Hint = list(it.product(OtherIDs,NumSuitSet))[ResultSelection]
        return Hint
        
    def GenerateCode(self,TurnNumber,HintingPlayer,CardNumberGroups,progress):
        # Iterates through a number of candidate codes (using common seed 
        # Monte Carlo) and selects the best based on some evaluation criteria
        OtherIDs = [m for m in range(self.nPlayers) if m != HintingPlayer]
        self.StartRandom(self.RandomSeedList[TurnNumber])
        SuitSetStr = ''
        for i in self.SuitSet:
            SuitSetStr += '[' + i +']' + ','
        SuitSetStr = '[' + SuitSetStr[:-1] +']'
        
        # For the various numerical subset groupings (including the trivial 
        # case where each value is its own subset) there is a number of DoF 
        # needed to transmit the information
        RequiredBase = [len(i) for i in CardNumberGroups]
        BaseSets = [[] for i in range(5)]
        BaseSets[4].append('0S')
        for i,I in enumerate(RequiredBase):
            BaseSets[I-1].append(str(i)+'N')
        
        ValidCombinations = []
        for i in self.NumSetCombo:
            PreProduct = []
            for j in i:
                if len(BaseSets[j-1]) > 0:
                    PreProduct.append(BaseSets[j-1])
            for j in list(it.product(*PreProduct)):
                if len(j) > 0:
                    ValidCombinations.append(j)
        
        nMCPerValidCombo = int(self.nMCCandidates/len(ValidCombinations))
            
        CodeCandidateList = []
        for i in ValidCombinations:
            for k in range(nMCPerValidCombo):
                TrialStr = ''
                for j in i:
                    TrialStr += j[-1]
                    TrialStr += '_'
                    ColComboChoice = random.randint(0,
                                            self.ColumnCombinations.shape[0]-1)
                    Cols =c(self.ColumnCombinations[ColComboChoice,:]).tolist()
                    ColInPlay = ([self.InPlay[TurnNumber][M,Cols[m]] 
                                    for m,M in enumerate(OtherIDs)])
                    for l,L in enumerate(ColInPlay):
                        if not L:
                            Cols[l] = -1
                    TrialStr +=  re.sub(' ','',str(Cols)[1:-1])
                    TrialStr += '_'
                    if j[-1] == 'S':
                        TrialStr += SuitSetStr
                    else:
                        TrialStr += re.sub(' ','',str(
                                    CardNumberGroups[int(j[:-1])]))
                    TrialStr += '__'
                CodeCandidateList.append(TrialStr[:-2])          
    
        BestReduction = 0
        BestCode = CodeCandidateList[0]
        for i,I in enumerate(CodeCandidateList):
            Reduction = self.EvaluateCode(OtherIDs,I,progress)
            if  Reduction > BestReduction:
                BestReduction = Reduction
                BestCode = I

        self.EndRandom()
        return BestCode

    def EvaluateCode(self,OtherIDs,Code,progress):
        # This function takes a code and returns an evaluation of the merit of
        # said code. Currently this takes the form of a degree of freedom (DoF)
        # minimization weighted by some coefficients (AMaster)
    
        # Weighting coefficients for determining set reduction. Currently just
        # naively the number of each card number in the deck
        AMaster = [3,2,2,2,1]
        P,D,O = self.GetPDO(progress)
        for i in P:
            AMaster[i-1] = AMaster[i-1] * 2.
        for i in D:
            AMaster[i-1] = AMaster[i-1] / 2.
        
        DoFReductionList = []
        
        CodeList = Code.split('__')
        TypeList = [i.split('_')[0] for i in CodeList]
        ColList = [i.split('_')[1] for i in CodeList]
        GroupSetList = [i.split('_')[2] for i in CodeList]
        
        NumIndex = [i for i,I in enumerate(TypeList) if I == 'N']
        SuitIndex = [i for i,I in enumerate(TypeList) if I == 'S']
        
        # Calculate numeric DoF reduction
        if len(NumIndex) > 0:
            NumColList = [ColList[i].split(',') for i in NumIndex]
            CodeNumSets = [eval(GroupSetList[i]) for i in NumIndex]
            NumColListSwitch = ([[int(NumColList[i][j]) 
                                for i in range(len(NumColList))] 
                                for j in range(len(NumColList[0]))])
            # This is the list of columns in each row that I need to check to
            # determine the reduction in uncertainty for a given code
            ColCheckList = [list(set(i)) for i in NumColListSwitch]
            
            for i,I in enumerate(ColCheckList):
                for j,J in enumerate(I):
                    InitialInfoSet = [int(m) for m in
                                     self.InformationMatrix[OtherIDs[i],J,'N']]
                    AParticular = [AMaster[m-1] for m in InitialInfoSet]
                    nPosFinal = []
                    for PosValInd,PossibleValue in enumerate(InitialInfoSet):
                        InfoSetRestrict = set(c(InitialInfoSet))
                        for k,K in enumerate(NumColListSwitch[i]):
                            if K == J:
                                InfoSetRestrict = InfoSetRestrict.intersection(
                                            [m for m in CodeNumSets[k] if 
                                            PossibleValue in m][0])
                       
                        nPosFinal.append(len(InfoSetRestrict))
                    DoFReduction = len(InitialInfoSet) - (
                        1./np.sum(AParticular)*np.sum([AParticular[m]*
                        nPosFinal[m] for m in range(len(AParticular))]))
                    DoFReductionList.append(DoFReduction)
                    
        # Calculate suit DoF reduction
        if len(SuitIndex) > 0:
            SuitColList = [ColList[i].split(',') for i in SuitIndex]
            SuitColListSwitch = ([[int(SuitColList[i][j]) 
                                for i in range(len(SuitColList))] 
                                for j in range(len(SuitColList[0]))])
            ColCheckList = [list(set(i)) for i in SuitColListSwitch]
            for i,I in enumerate(ColCheckList):
                for j,J in enumerate(I):
                    InitialInfoSet = [m for m in
                                     self.InformationMatrix[OtherIDs[i],J,'S']]
                    DoFReduction = len(InitialInfoSet) - 1
                    DoFReductionList.append(DoFReduction)
        return np.sum(DoFReductionList)



    def Startup(self,r):
        # Currently rainbow compatability is not implemented
        if r.suits != 'rygbw':
            raise NameError('Encoding AI requires vanilla suits\n')
            
        for i in r.NameRecord:
            if i[:-1] != 'Gencoder':
                raise NameError('Encoding AI must only play with other' + 
                                ' encoders')                                
        self.InitializeConstants(r)

    def StartRandom(self,seed):
        # This function initializes the fixed seed random method used by
        # players. There is a concern that the use of this method, particularly
        # the setting of a fixed seed, may bias other functions which wish to 
        # call random. For this reason, the RNG state is recorded at the start 
        # of the player call; the RNG state will then be set back to this state
        # before the player concludes it's turn. This will prevent the fixed
        # seed method from interacting with other random calls outside of the
        # AI program.
        self.RNG_State = random.getstate()
        random.seed(seed)
        
    def EndRandom(self):
        # This function is responsible for returning the RNG to the same state
        # as when it entered the AI        
        random.setstate(self.RNG_State)
        
    
    def StaticCombinatorics(self):
        # This function performs the combinatoric math which only needs to be
        # done once (even across replicate games)
    
        # This array represents the combination of cards in other players'
        # hands. Each row is a different possibility. The columns are 
        # associated with the indicies of the other players (that is, there 
        # are nPlayers - 1 columns). This array should be called with the 
        # appropriate OtherID vector (not necessarily the current player's).
        # The numeric value in the array represents the positional index of a 
        # card. Note that this format intentionally disallows multiple cards
        # in the same player's hand to be selected as this introduces 
        # non-uniqueness into the modular arithmetic algebra. Also note that a
        # card is chosen from every other hand. In the chose encoding method,
        # there is no benefit to encoding fewer cards, so reencoding already
        # determined cards is fine; by contrast encoding a number less than
        # nPlayers - 1 in a single value would further conbinatorically grow
        # the number of choices. (Unnecessarily)
        IndexVector = [i for i in range(self.nCards)]
        self.ColumnCombinations = np.array(list(it.product(IndexVector,
                                                    repeat=self.nPlayers-1)))
                                                    
    def GetPDO(self,progress):
        # Utility to get the set of playable (P), discardable (D),
        # and other (O)
        NumericVec =  [progress[key] for key in progress]
        
        P = list(np.unique(
            [i + 1 for i in NumericVec if i < self.MaxCardNumber]))
        D = [int(i) for i in self.NumberSet if int(i) < np.min(P)]
        O = list(set([int(i) for i in self.NumberSet]).difference(
            set(P).union(D)))
        return P,D,O
    
    def GroupCardNumbers(self,progress):
        # This function accepts a progress dictionary (not necessarily the 
        # current one) and generates the grouped sets for the card number 
        # encoding. That is to say, one can use less than a full quint (base
        # 5 bit) and transmit only some information about the numeric value of 
        # a card. This is currently not implemented with suits, as the suits
        # are equivilent in a way that the numbers are not, and implementing
        # a similar convention is not currently worth the extra effort and
        # complexity.
    
        # P is the playable set. Elements in P have at least one suit where
        # playing a card with a value equal to said element is a legal move
    
        # D is the strict discard set. There is no suit for which a a card
        # whose value is in D is a legal move
    
        # O is the "other" set. Elements of self.NumberSet which are not in P 
        # or D fall in O:
        # O = self.NumberSet \ (P U D)
    
        # Suit identity is not important for this operation
        P,D,O = self.GetPDO(progress)
        
        # This code constructs the numeric grouping sets used during incomplete
        # encoding (in order to use less than a full quint)
        NumericSets = []
        
        # [[D],P+O]
        NumericSets.append([])
        if len(D) > 0: NumericSets[-1].append(D)
        for i in P:
            NumericSets[-1].append([i])
        for i in O:
            NumericSets[-1].append([i])
            
        # [[D],P,[O]]
        NumericSets.append([])
        if len(D) > 0: NumericSets[-1].append(D)
        for i in P:
            NumericSets[-1].append([i])
        if len(O) > 0: NumericSets[-1].append(O)
            
        # [[P],[D+O]]
        if len(D) + len(O) > 0:
            NumericSets.append([])   
            NumericSets[-1].append(P)
            NumericSets[-1].append(list(set(D).union(O)))

        
        # Variable end grouping sets
        for k in range(len(D)+len(P),self.nCards):
            NumericSets.append([])
            if len(D) > 0: NumericSets[-1].append(D)
            for i in P:
                NumericSets[-1].append([i])
            OSplit1 = O[:k-[1 if len(D)>0 else 0][0]-len(P)]
            OSplit2 = O[k-[1 if len(D)>0 else 0][0]-len(P):]
            for i in OSplit1:
                NumericSets[-1].append([i])
            if len(OSplit2) > 0:
                NumericSets[-1].append(OSplit2)
            
        UniqNumericSets = []
        for i in NumericSets:
            if i not in UniqNumericSets:
                if len(i) > 1:
                    UniqNumericSets.append(i)

            
        return UniqNumericSets
    
    def PrintInfoMat(self,row = ''):
        # Prints the current state of the information matrix in an aestetically
        # pleasing fashon.
        if row == '':
            playerRange = range(self.nPlayers)
        else:
            playerRange = [row]
        N = [['' for m in range(self.nCards)] for n in range(self.nPlayers)]
        S = [['' for m in range(self.nCards)] for n in range(self.nPlayers)]
        for i in playerRange:
            for j in range(self.nCards):
                N[i][j] += '['
                for m in self.InformationMatrix[i,j,'S']:
                    N[i][j] += m + ','
                N[i][j] = N[i][j][:-1] + ']'
                S[i][j] = '['
                for m in self.InformationMatrix[i,j,'N']:
                    S[i][j] += m + ','
                S[i][j] = S[i][j][:-1] + ']'
        NStrLenList = []
        SStrLenList = []
        for j in range(self.nCards):
            NStrLen = 0
            SStrLen = 0
            for i in playerRange:
                if len(N[i][j]) > NStrLen:
                    NStrLen = len(N[i][j])
                if len(S[i][j]) > SStrLen:
                    SStrLen = len(S[i][j])
            NStrLenList.append(NStrLen)
            SStrLenList.append(SStrLen)
        for i in playerRange:
            for j in range(self.nCards):
                print((str(S[i][j]) + ' '*(SStrLenList[j] - len(S[i][j])) + 
                       str(N[i][j]) + ' '*(NStrLenList[j] + 5 - len(N[i][j]))),)
            print('')

        
        
        
        
