# -*- coding: utf-8 -*-
"""
Created on Sun Apr 17 15:11:03 2016

@author: robieta
"""

from copy import deepcopy as c
import itertools as it
import numpy as np
#import sys
#import random
#
#from hanabi_classes import *

# This AI is designed to implement an information encoding algorithm
# Still very much a work in progress

class EncodingPlayer:
    def __init__(self):
        pass
        
    def InitializeConstants(self,r):
        self.nPlayers = r.nPlayers
        self.SelfID = r.whoseTurn
        self.OtherIDs = [i for i in range(r.nPlayers) if i != self.SelfID]
        self.suits = r.suits
        
        #Encoding tables give a definitive way to convery a hint given into a numeric value
        self.EncodingTables = []
        for l in range(r.nPlayers):
            self.EncodingTables.append([[i,str(j)] for j in '12345rygbw' for i in [k for k in range(r.nPlayers) if k != l]])
        self.TableSize = len(self.EncodingTables[self.SelfID])
        
        self.nCards = len(r.h[r.whoseTurn].cards)
        
        self.SuitStr = ''
        for k in r.suits: self.SuitStr += k + ','
        self.SuitStr = self.SuitStr[:-1]
        self.NumStr = '1,2,3,4,5'
        
        self.SortedDeck = []
        for suit in self.suits:
            for number in '1112233445':
                self.SortedDeck.append(number + suit)
        
        
        
        #First element is suit, second is numeric value
        self.InformationMatrix = self.CompleteHandToInt(r,range(self.nPlayers),0)
        
        self.RunningPlayInd = -1
        self.iRecord = -1
        
        self.CodeList = []
        self.CodeList.append('0N_1,2+__1N_1,2+__2N_1,2+__2S_all')
        self.CodeList.append('0N_1-4+__3S_all__3N_1,2+')
        self.CodeList.append('4S_all_3,1:0,2:1,3__4N_1,2+_0,2:1,3__1N_1-4+')
        self.CodeList.append('0S_all__1S_all')
        
    
    def play(self, r):
        nPriorTurns = len(r.playHistory)
        if r.suits != 'rygbw':
            raise NameError('Encoding AI requires vanilla suits\n')
        for i in r.NameRecord:
            if i.split('_')[0] != 'Encoding':
                raise NameError('Encoding AI must only play with other encoders')
        if r.nPlayers != 5:
            raise NameError('Encoding AI must play in a 5 player game')
            
        if nPriorTurns <= r.nPlayers - 1:
            self.InitializeConstants(r)

        for i,I in enumerate(r.playHistory):            
            if i > self.iRecord:
                self.iRecord = c(i)
                if i == len(self.CodeList):
                    self.CodeList.append('')
                PlayingPlayer = (i % self.nPlayers) # Determines which player made this move
                if I[0] == 'hint':
                    GivenHint = list(I[1])
                    if self.CodeList[i] == '':
                        NumInHand =  [len(K.cards) for K in r.HandHistory[i]]
                        self.CodeList[i] = self.CodeFromInfoMat(PlayingPlayer,NumInHand)
                    Code = self.CodeList[i]
                    EncodedValue = self.BackOutEncodedValue(self.EncodingTables[PlayingPlayer],GivenHint)
                    for j in [k for k in range(self.nPlayers) if k != PlayingPlayer]:
                        RestrictedDenseOtherHands = self.CompleteHandToInt(r,[j,PlayingPlayer],i)
                        self.ValueFromCode(Code,RestrictedDenseOtherHands,EncodedValue,j)
                    
                    if GivenHint[1] in '12345':
                        HintType = 'N'
                    elif GivenHint[1] in r.suits:
                        HintType = 'S'
                    else:
                        raise NameError('')
                        
                    MatLabel = {'N':'NumMat','S':'SuitMat'}[HintType]
                    for j,J in enumerate(r.HandHistory[i][GivenHint[0]].cards):
                        
                        PriorKnowedge = c(self.InformationMatrix[MatLabel][GivenHint[0],j])
                        if PriorKnowedge == 'x':
                            if HintType == 'N':
                                PriorKnowedge = self.NumStr
                            else:
                                PriorKnowedge = self.SuitStr
                        else:
                            if HintType == 'S':
                                if len(PriorKnowedge) == 1:
                                    PriorKnowedge = str([r.suits[int(k)] for k in PriorKnowedge.split(',')])[1:-1]
    
                        DirectSet = list(set(PriorKnowedge.split(',')).intersection(J['direct']))
                        if len(DirectSet) == 1:
                            pass
                            if HintType == 'S':
                                self.InformationMatrix[MatLabel][GivenHint[0],j] = c([str(k) for k,K in enumerate(r.suits) if K == DirectSet[0]][0])
                            else:
                                self.InformationMatrix[MatLabel][GivenHint[0],j] = c(DirectSet[0])
                        else:
                            StrictIndirect = set(J['indirect']) - set(J['direct'])
                            IndirectSet = set(PriorKnowedge.split(',')) - StrictIndirect
                            
                            #Currently only use indirect method for numeric hints
                            if HintType == 'N':
                                self.InformationMatrix[MatLabel][GivenHint[0],j] = c(str([int(k) for k in IndirectSet])[1:-1])
                        
                        if len(self.InformationMatrix[MatLabel][GivenHint[0],j]) == 0:
                            raise NameError('Error: Possibility has been reduced to empty set')      
                      
                    self.CheckEncoding(r,i+1)
                elif I[0] == 'play' or I[0] == 'discard':
                    self.RunningPlayInd += 1                
                    for key in self.InformationMatrix:
                        for j in range(r.DropIndRecord[self.RunningPlayInd]+1,self.nCards):                    
                            self.InformationMatrix[key][PlayingPlayer,j-1] = (
                                c(self.InformationMatrix[key][PlayingPlayer,j]))
    
                        self.InformationMatrix[key][PlayingPlayer,-1] = 'x'
                    
                    self.CheckEncoding(r,i+1)
                else:
                    raise NameError('Unknown action')
                          
            
            
        
        cards = r.h[r.whoseTurn].cards # don't look!
        DenseOtherHands = self.CompleteHandToInt(r,[self.SelfID])

        # The first 4 turns are hard coded
        if nPriorTurns < 4:
            Code = self.CodeList[nPriorTurns]
            EncodedValue,ResultList = self.InterpretCode(Code,DenseOtherHands)
            Hint = self.EncodingTables[self.SelfID][EncodedValue]
            return 'hint', (Hint[0],Hint[1])
        
        PlayInd = self.GetPlayInd(r.progress)
        if PlayInd != -1:
            return 'play',cards[PlayInd]
            
        DiscardList = self.GetDiscardable(r)
        if len(DiscardList) > 0 and r.hints < self.nPlayers-1:
            return 'discard',cards[DiscardList[0]]
        
        if r.hints > 0:
            NumInHand = [len(K.cards) for K in r.h]
            NewCode = self.CodeFromInfoMat(self.SelfID,NumInHand)    
            EncodedValue,ResultList = self.InterpretCode(NewCode,DenseOtherHands)
            Hint = self.EncodingTables[self.SelfID][EncodedValue]
            return 'hint', (Hint[0],Hint[1])
        
        
        return 'resign', ''

    def CodeFromInfoMat(self,CurrentPlayer,NumInHand):        
        OtherPlayers = [i for i in range(self.nPlayers) if i != CurrentPlayer]
        HandNumOther = [NumInHand[K] for K in OtherPlayers]
        NumPosMat = np.zeros([self.nPlayers,self.nCards])
        SuitPosMat = np.zeros([self.nPlayers,self.nCards])
        for i,I in enumerate(self.InformationMatrix['NumMat']):
            for j,J in enumerate(I):
                KnownStr = c(J)
                if KnownStr == 'x': KnownStr = self.NumStr
                NumPosMat[i,j] = len(KnownStr.split(','))
        for i,I in enumerate(self.InformationMatrix['SuitMat']):
            for j,J in enumerate(I):
                KnownStr = c(J)
                if KnownStr == 'x': KnownStr = self.SuitStr
                SuitPosMat[i,j] = len(KnownStr.split(','))
        
        CandidateIndicies = list(it.product(range(self.nCards),repeat=self.nPlayers-1))
        ReductionListNum = []
        ReductionListSuit = []
        for i,I in enumerate(CandidateIndicies):
            nReductionNum = 0
            nReductionSuit = 0
            for j,J in enumerate(I):
                nReductionNum += NumPosMat[OtherPlayers[j],J] - 1
                nReductionSuit += SuitPosMat[OtherPlayers[j],J] - 1
            ReductionListNum.append(int(nReductionNum))
            ReductionListSuit.append(int(nReductionSuit))
        NumSortInd = np.argsort(ReductionListNum)[::-1]
        SuitSortInd = np.argsort(ReductionListSuit)[::-1]
        
        MaxReduction = np.max([np.max(ReductionListNum),np.max(ReductionListSuit)])
        CodeCandidateList = []
        for i in range(0,MaxReduction+1)[::-1]:
            # Prioritize number resolution over suit resolution
            for j in range(len(NumSortInd)):
                if ReductionListNum[NumSortInd[j]] == i:
                    ColInd = list(CandidateIndicies[NumSortInd[j]])
                    if all([HandNumOther[k] > K for k,K in enumerate(ColInd)]):
                        CodeCandidateList.append('N:' + str(ColInd)[1:-1])
            for j in range(len(SuitSortInd)):
                if ReductionListNum[SuitSortInd[j]] == i:
                    ColInd = list(CandidateIndicies[SuitSortInd[j]])
                    if all([HandNumOther[k] > K for k,K in enumerate(ColInd)]):
                        CodeCandidateList.append('S:' + str(ColInd)[1:-1])
        
        CodeSelection = [CodeCandidateList[0]]
        for i in CodeCandidateList:
            if i[0] != CodeSelection[0][0]:
                CodeSelection.append(i)
                break
            else:
                ColInd = [int(k) for k in i.split(':')[1].split(',')]
                if not any(np.equal([int(k) for k in CodeSelection[0].split(':')[1].split(',')],
                                     ColInd)):
                     CodeSelection.append(i)
                     break
        CodeStr = ''
        for I in CodeSelection:
            CodeStr += '4' + I[0] + '_all_'
            for j,J in enumerate([int(K) for K in I.split(':')[1].split(',')]):
                CodeStr += str(OtherPlayers[j]) + ',' + str(J) + ':'
            CodeStr = CodeStr[:-1]
            CodeStr += '__'
        CodeStr = CodeStr[:-2]
        return CodeStr
    
    def GetDiscardable(self,r):
        Output = []
        CardCount = {i:0 for i in np.unique(self.SortedDeck)}
        for i in self.SortedDeck:
            CardCount[i] += 1
        for i,I in enumerate(r.playHistory):
            if I[0] == 'play' or I[0] == 'discard':
                CardCount[I[1]['name']] -= 1
            elif I[0] == 'hint':
                pass
            else:
                raise NameError('')
        
        for i in range(self.nCards):
            NumMatStr = c(self.InformationMatrix['NumMat'][self.SelfID,i])
            if NumMatStr == 'x': NumMatStr = self.NumStr
            SuitMatStr =  c(self.InformationMatrix['SuitMat'][self.SelfID,i])
            if SuitMatStr == 'x': SuitMatStr = str(range(5))[1:-1]
            

            SuitList =  [self.SuitStr.split(',')[l] for l in 
                        [int(k) for k in SuitMatStr.split(',')]]
            NumList  =  [str(int(k)) for k in NumMatStr.split(',')]
            PosList  = list(it.product(SuitList,NumList))
            
            SafeDiscard = True
            for J in PosList:
                if CardCount[J[1] + J[0]] < 2:
                    SafeDiscard = False
                    break
            if SafeDiscard:
                Output.append(i)
        return Output


    def GetPlayInd(self,Progress):
        Playable = self.GetPlayableCards(Progress)
        if len(Playable['PlayableInd']) == 0:
            return -1
        Max_nPossible = np.max(Playable['nPossible'])
        newCandidates = [K for k,K in enumerate(Playable['PlayableInd']) if Playable['nPossible'][k] == Max_nPossible]
        return newCandidates[0]
        
    
    def GetPlayableCards(self,Progress):
        Output = {'PlayableInd':[],'nPossible':[]}        
        ValidPlays = []
        for key in Progress:
            ValidPlays.append(key + str(Progress[key]+1))
        
        for i in range(self.nCards):
            PossibleCards = []
            SuitInfo = c(self.InformationMatrix['SuitMat'][self.SelfID,i])
            if SuitInfo == 'x': SuitInfo = str(range(5))[1:-1]
            NumInfo = c(self.InformationMatrix['NumMat'][self.SelfID,i])
            if NumInfo == 'x': NumInfo = c(self.NumStr)
                
            SuitInd = [int(k) for k in SuitInfo.split(',')]   
            NumInd = [int(k) for k in NumInfo.split(',')] 
            SuitList = [self.SuitStr.split(',')[k] for k in SuitInd]
            NumList = [str(k) for k in NumInd]
            
            for J in it.product(SuitList,NumList):
                PossibleCards.append(J[0] + J[1])
            
            Playable = len(set(PossibleCards).intersection(ValidPlays)) == len(PossibleCards)
            if Playable:
                Output['PlayableInd'].append(i)
                Output['nPossible'].append(len(PossibleCards))
        return Output
        
    def CompleteHandToInt(self,r,Exclude=[],Turn='current'):
        # This function converts the standrd hand structure into a more compact
        # form for mathematical functions
        if Turn == 'current':
            Hand = r.h
        elif Turn == len(r.HandHistory):
            Hand = r.h
        else:
            Hand = r.HandHistory[Turn]
    
        NumMat = np.zeros([r.nPlayers,self.nCards]).tolist()
        SuitMat = np.zeros([r.nPlayers,self.nCards]).tolist()
        for i in range(r.nPlayers):
            for j,J in enumerate(Hand[i].cards):
                if i not in Exclude:
                    NumMat[i][j] = int(J['name'][0])
                    SuitMat[i][j] = [k for k,K in enumerate(r.suits) if K == J['name'][1]][0]
                else:
                    NumMat[i][j] = 'x'
                    SuitMat[i][j] = 'x'
        NumMat = np.array(NumMat,dtype='S64')
        SuitMat = np.array(SuitMat,dtype='S64')
        return {'NumMat':NumMat,'SuitMat':SuitMat}
        
    def EnumerateMixedBase(self,BaseIn):
        Output = range(BaseIn[0])
        for i,I in enumerate(BaseIn[1:]):
            Output = np.array(list(it.product(Output,range(I)))).tolist()
            if i>0:
                for j,J in enumerate(Output):
                    Output[j] = list(it.chain(*[J[0],[J[1]]]))
        for i,I in enumerate(Output):
            if type(I) != list:
                Output[i] = [Output[i]]
        
        return Output
        
    def InterpretCode(self,Code,DenseOtherHands):
        ResultList = []
        MixBaseList = []
        for i,I in enumerate(Code.split('__')):
            Position,Map,OtherHandMat,MatLabel,CustomPosition = self.CodeParse(I,DenseOtherHands)

            if Position != 'custom':
                OtherHandRaw = OtherHandMat[self.OtherIDs,Position]
            else:
                OtherHandRaw = [OtherHandMat[j[0],j[1]] for j in CustomPosition]
            
            OtherHandMapped = self.MapVector(OtherHandRaw,Map)           
            
            ResultList.append(np.sum(OtherHandMapped) % len(Map[1]))
            MixBaseList.append(len(Map[1]))

        MixBaseEnum = self.EnumerateMixedBase(MixBaseList)
        for i,I in enumerate(MixBaseEnum):
            if np.array_equal(I,ResultList):
                return i,ResultList

 
    def ValueFromCode(self,Code,DenseOtherHands,EncodedValue,Player):
        MixBaseList = []
        for i,I in enumerate(Code.split('__')):
            Position,Map,OtherHandMat,MatLabel,CustomPosition = self.CodeParse(I,DenseOtherHands)
            MixBaseList.append(len(Map[1]))
            
        MixBaseEnum = self.EnumerateMixedBase(MixBaseList)
        ResultList = MixBaseEnum[EncodedValue]
        
        BackCalcList = []
        for i,I in enumerate(Code.split('__')):
            AdjustInfoMatBool = True
            Position,Map,OtherHandMat,MatLabel,CustomPosition = self.CodeParse(I,DenseOtherHands)
            if Position != 'custom':
                OtherValues = [int(j) for j in OtherHandMat[:,Position] if j != 'x']
                if len(OtherValues) != self.nPlayers - 2:
                    raise NameError('Incorrect number of elements')

            else:
                PlayerAddress = []
                OtherPlayerAddress = []
                for j,J in enumerate(CustomPosition):
                    if J[0] == Player:
                        PlayerAddress.append(J)
                    else:
                        OtherPlayerAddress.append(J)
                
                if len(PlayerAddress) > 1:
                    raise NameError('Multiple unknowns for same player not supported')
                elif len(PlayerAddress) == 1:
                    PlayerAddress = PlayerAddress[0]
                    OtherValues = [OtherHandMat[j[0],j[1]] for j in OtherPlayerAddress]
                else:
                    AdjustInfoMatBool = False
                  
            if AdjustInfoMatBool:
                MappedOtherValues = self.MapVector(OtherValues,Map)
                ResultInd = (ResultList[i] - np.sum(MappedOtherValues)) % len(Map[1])
                BackCalcList.append(self.InverseMapVector([ResultInd],Map)[0])
                
                if Position != 'custom':  
                    PlayerAddress = [Player,Position]
    
                CurrentKnowledge = c(self.InformationMatrix[MatLabel][PlayerAddress[0],PlayerAddress[1]])
                
                AddedKnowledge = str(BackCalcList[-1])[1:-1]
                if CurrentKnowledge == 'x':
                    self.InformationMatrix[MatLabel][PlayerAddress[0],PlayerAddress[1]] = c(AddedKnowledge)
                elif len(CurrentKnowledge) == 1:
                    pass
                else:
                    CurrentSet =  [int(j) for j in AddedKnowledge.split(',')]
                    IntSet = [int(j) for j in CurrentKnowledge.split(',')]
                    NewSet = list(set(CurrentSet).intersection(IntSet))
                    if len(NewSet) == 0:
                        raise NameError('Error: Possibility has been reduced to empty set')
                    self.InformationMatrix[MatLabel][PlayerAddress[0],PlayerAddress[1]] = c(str(NewSet)[1:-1])    
        
    def CodeParse(self,CodeIn,DenseOtherHands):
        Position = int(CodeIn.split('_')[0][0])
        if Position >= DenseOtherHands['NumMat'].shape[1]:
            Position = 'custom'
            CustomPosition = [[int(j) for j in i.split(',')] 
                                for i in CodeIn.split('_')[2].split(':')]
        else:
            Position = int(Position)
            CustomPosition = ''
        MatLabel = {'N':'NumMat','S':'SuitMat'}[CodeIn.split('_')[0][1]]
        OtherHandMat = c(DenseOtherHands[MatLabel])
        if CodeIn.split('_')[1] == 'all':
            if CodeIn.split('_')[0][1] == 'N':
                Map = [[[1],[2],[3],[4],[5]],range(5)]
            elif CodeIn.split('_')[0][1] == 'S':
                Map = [[[0],[1],[2],[3],[4]],range(5)]
        elif CodeIn.split('_')[1] == '1,2+':
            if CodeIn.split('_')[0][1] == 'N':
                Map = [[[1],[2,3,4,5]],[1,0]]
            else:
                raise NameError('1,2+ valid only for numeric case')   
        elif CodeIn.split('_')[1] == '1-4+':
            if CodeIn.split('_')[0][1] == 'N':
                Map = [[[1],[2],[3],[4,5]],[0,1,2,3]]
            else:
                raise NameError('1-4+ valid only for numeric case')  
            
        return Position,Map,OtherHandMat,MatLabel,CustomPosition
        
    def MapVector(self,VecIn,Map):
        VecOut = []        
        for i in VecIn:
            for j,J in enumerate(Map[0]):
                if int(i) in J:
                    VecOut.append(Map[1][j])
        return VecOut
        
    def InverseMapVector(self,VecIn,Map):
        OutVec = []
        for i in VecIn:
            for j,J in enumerate(Map[1]):
                if i==J:
                    OutVec.append(Map[0][j])
        return OutVec
        
    def BackOutEncodedValue(self,EncodingTable,Hint):
        for i,I in enumerate(EncodingTable):
            if np.array_equal(I,Hint):
                return i
    
    def CheckEncoding(self,r,Turn):
        # Debuging function to check if an incorrect value has been encoded
        RigorousOtherHands = self.CompleteHandToInt(r,[],Turn)
        for key in RigorousOtherHands:
            for i,I in enumerate(RigorousOtherHands[key]):
                for j,J in enumerate(I):
                    if self.InformationMatrix[key][i,j] != 'x':
                        KnownSpace = [int(k) for k in self.InformationMatrix[key][i,j].split(',')]
                        KnownIntersectActual = len(set(KnownSpace).intersection([int(k) for k in J]))
                        if KnownIntersectActual == 0:
                            self.InfoMatHumanReadable()  
                            print r.h[i].cards
                            print r.h[i].cards[j]
                            raise NameError('Incorrect value detected in encoding scheme: [' 
                                    + str(i) + ',' + str(j) + ']')


    def InfoMatHumanReadable(self):
        print ''
        InfoMatPrint = c(self.InformationMatrix)
        MaxLen = 0
        for key in InfoMatPrint:
            for j,J in enumerate(self.InformationMatrix[key]):
                for k,K in enumerate(J):
                    if key == 'SuitMat' and K != 'x':
                        Temp1 = ''
                        for m in [int(l) for l in K.split(',')]:
                            Temp1 += self.suits[m]
                        InfoMatPrint[key][j,k] = Temp1
                        K=InfoMatPrint[key][j,k]

                    MaxLen = np.max([MaxLen,len(K)])
            def PadStr(Str,Len):
                for i in range(Len-len(Str)):
                    Str += ' '
                return Str
            
        for key in InfoMatPrint:
            print key    
            for J in InfoMatPrint[key]:
                for K in J:
                    if K=='x':
                        PrintStr = ''
                    else:
                        PrintStr = K
                    print PadStr(PrintStr,MaxLen) + ' |' + ' '*4,
                print ''
            print ''
    
    
    
    
    