from __future__ import print_function
import pygame,time,random
from itertools import permutations,izip 
import shelve
import inputbox
from operator import itemgetter
pygame.init()
display_width,display_height=(600,600)
FPS=1
smallfont=pygame.font.SysFont('comicsansms',20)
medfont=pygame.font.SysFont('comicsansms',30)
largefont=pygame.font.SysFont('comicsansms',40)
white=(255,255,255)
black=(0,0,0)
red=(199,0,0)
green=(0,111,0)
blue=(0,0,199)
clock=pygame.time.Clock() 
wins=set()
win_combis=[[0,1,2],[3,4,5],[6,7,8],[0,3,6],[1,4,7],[2,5,8],[0,4,8],[2,4,6]]
turn=False
mode=None #true when training and false when playing against
db=shelve.open('qvalues')
Q={} #q values vector
GamesTrained=None
GamesWon=None
GamesTied=None
try:
    Q=db['ku']
except KeyError:
    Q[(0,0)]=[0 for _ in xrange(9)]
    Q[(0,1)]=[0 for _ in xrange(9)]
    Q[(0,2)]=[0 for _ in xrange(9)]
    Q[(1,0)]=[0 for _ in xrange(9)]
    Q[(1,1)]=[0 for _ in xrange(9)]
    Q[(1,2)]=[0 for _ in xrange(9)]
    Q[(2,0)]=[0 for _ in xrange(9)]
    Q[(2,1)]=[0 for _ in xrange(9)]
    Q[(2,2)]=[0 for _ in xrange(9)]
    db['ku']=Q
try:
    GamesTrained=db['gt']
except KeyError:
    GamesTrained=0
    db['gt']=GamesTrained
try:
    GamesWon=db['gw']
except KeyError:
    GamesWon=0
    db['gw']=GamesWon
try:
    GamesTied=db['tt']
except KeyError:
    GamesTied=0
#Q=[-1,1.5,2.5,3.0,4.5,3.5,1,0,-2]
alpha=0.60  #alpha must decrease but not too quickly 0.5 for now 
expDict={ 0 : set((1,2,3,6,4,8)) , 1 : set((0,2,4,7)) , 2 : set((0,1,5,8,4,6)) ,
   3 : set((0,6,4,5)) , 4 : set((0,1,2,3,5,6,7,8)) , 5 : set((3,4,2,8)),
   6 : set((0,3,7,8,4,2)) , 7 : set((1,4,6,8)) , 8 : set((6,7,0,4,5,2))
}
for combi in win_combis:
    for permu in permutations(combi):
        wins.add(permu)
#game clock 
#put global vars or vars used through out here
gameDisplay=pygame.display.set_mode((display_width,display_height)) #get surface object
pygame.display.set_caption('Teaching Tic-Tac-Toe') #put icon later 

def text_objects(text,color,size): #function to generate text object with rectangle 
    if size=='small':
        textsurface=smallfont.render(text,True,color)
    elif size=='medium':
        textsurface=medfont.render(text,True,color)
    elif size=='large':
        textsurface=largefont.render(text,True,color)
    return textsurface,textsurface.get_rect()
def message_to_screen(msg,color,y_displace=0,size='small'):
    textsurface,textrect=text_objects(msg,color,size)
    textrect.center=(display_width//2),(display_height//2)+y_displace
    gameDisplay.blit(textsurface,textrect)

def game_intro(): #define intro screen that shows options to train or play against
    intro=True
    global mode
    global turn
    global GamesTrained
    global GamesWon
    while intro:
        for event in pygame.event.get():
            if event.type==pygame.KEYDOWN:
                if event.key==pygame.K_t:
                    intro=False    #must move to training screen for now quits
                    turn=False
                    mode=True
                    game_loop(mode)
                if event.key==pygame.K_p:  #must move to versus screen for noq quits 
                    intro=False
                    turn=False
                    mode=False
                    game_loop(mode)
            if event.type==pygame.QUIT:
                intro=False
                pygame.quit()
                quit()
        gameDisplay.fill(black)
        message_to_screen('Welcome to tic-tac-toe',red,-100,'large')
        message_to_screen('Press T to train or P to play',blue,-30,'medium')
        message_to_screen('GamesTrained : '+str(GamesTrained),green,120,'small')
        message_to_screen('GamesWon : '+str(GamesWon),green,160,'small')
        message_to_screen('GamesTied : '+str(GamesTied),green,200,'small')
        pygame.display.update()
        clock.tick(FPS)
# moves=[m for m,p in enumerate(board_config) if p==player1 (or) player2]
def who_won(board_config):
    moves=[m for m,p in enumerate(board_config) if p==1] #get moves made by player 1
    for seq in permutations(moves,3):
        if seq in wins:
            return 'P1 wins' #ret val when p1 wins                  #do action when player 1 wins
    moves=[m for m,p in enumerate(board_config) if p==2] #get moves made by player 2
    for seq in permutations(moves,3):
        if seq in wins:
            return 'P2 wins'
    if 0 in board_config:
        return ''
    else:
        return 'tie'
    #similarly for player 2 if not both tie 
#needs to be improved 

def game_loop(mode):  #initialize board for training or versus for now seems like it,needs to run a minimum of two auxillary functions for q values and one for using them 
    global Q
    global alpha
    global turn
    global GamesTrained
    global GamesWon
    global db
    global expDict
    global GamesTied 
    board=[ 0 for _ in xrange(9)] #initialize empty board 0 empty p1 is 1 and p2 is 2 
    game_exit=False #completetly exit the game
    game_over=False #either player wins take action
    square_map={0:(0,0,200,200) , 1:(200,0,200,200) , 2:(400,0,200,200) , 3:(0,200,200,200),
     4:(200,200,200,200), 5:(400,200,200,200), 6:(0,400,200,200), 7:(200,400,200,200), 8:(400,400,200,200)
    } #maps  tile pos to coords for drawing squares
    pos_map={ (0,0):0, (1,0):1, (2,0): 2, (0,1):3, (1,1):4, (2,1):5,
        (0,2):6 , (1,2):7, (2,2):8
    } #to map mouse click coords use //200 
    update_list=[square_map[x] for x in xrange(9)] #for permmanent updates to achieve partial updates
    #turn refers to cpu's turn turn True means Cpu gotta play 
    plays_first=2 # 1 when cpu plays first else 2 , 1 when boltzmann plays else 2
    if random.randint(1,2)==1:
        turn=True
        plays_first=1
    
    def dumb_player(player_num): #function to play foolishly
           # global turn 
            pos=None
            #if turn:
            empty_positions=[e for e,o in enumerate(board) if o==0] #find empty spots on the board from there place randomly
            if empty_positions!=[] and who_won(board)=='':    
                pos=random.choice(empty_positions)
                board[pos]=player_num #make the guess move
                return pos
                #turn=False #move made 
                #draw_square(pos,blue)
        #if who_won(board)!='':
            #    game_over=True
            
    
    def draw_square(which_square,which_color): # a number between 0-8 inclusive
        #pygame.draw.rect(surface_obj,color,rect,thickness) ,rect is (x,y,width,height) where (x,y) upper left corner
       # rect=pygame.draw.rect(gameDisplay,which_color,square_map[which_square],0)
        squire=square_map[which_square]
        gameDisplay.fill(which_color,squire)    
        pygame.display.update(update_list)
        if squire in update_list:
            update_list.remove(squire)
        pygame.time.delay(1000)
    
    def smart_player(player_num): #use Q-values
        global turn
        global win_combis
        pos=None
        opp_num=None
        block_index=-1
        wewe=-1
        win_flag=False
        flag=False
        if turn:
            empty_positions=[e for e,o in enumerate(board) if o==0]
            empty_posit=set(empty_positions)
            if empty_positions!=[] and who_won(board)=='':
                if player_num not in board: #aka first move
                    lis=((x,len(expDict[x])) for x in empty_positions)## generator risk #we need to pick pos with max len in expDict
                    pos=max(lis,key=itemgetter(1))[0]
                    board[pos]=player_num #make the guess move
                    turn=False #move made 
                    draw_square(pos,blue)
                    return
                else: #we made a move ..two approaches , one use Q to get move(lyt), assume move use Q to decide (seems legit)
                    for x,y,z in win_combis:
                        wewe+=1
                        empcunt=0
                        ourcunt=0
                        if board[x]==player_num:
                            ourcunt+=1
                        elif board[x]==0:
                            empcunt+=1
                        if board[y]==player_num:
                            ourcunt+=1
                        elif board[y]==0:
                            empcunt+=1
                        if board[z]==player_num:
                            ourcunt+=1
                        elif board[z]==0:
                            empcunt+=1
                        if ourcunt==2 and empcunt==1:
                            win_flag=True
                            break
                    liz=[]
                    player_tiles=set([x for x,y in enumerate(board) if y==player_num])
                    if player_num==1:
                        opponent_tiles=set([x for x,y in enumerate(board) if y==2])
                        opp_num=2
                    else:
                        opponent_tiles=set([x for x,y in enumerate(board) if y==1])
                        opp_num=1
                    for x,y,z in win_combis:
                        block_index+=1
                        empcount=0
                        oppcount=0
                        if board[x]==opp_num:
                            oppcount+=1
                        elif board[x]==0:
                            empcount+=1
                        if board[y]==opp_num:
                            oppcount+=1
                        elif board[y]==0:
                            empcount+=1
                        if board[z]==opp_num:
                            oppcount+=1
                        elif board[z]==0:
                            empcount+=1
                        if oppcount==2 and empcount==1:
                            flag=True
                            break
                    for emp in empty_positions:
                        idx_one=len(expDict[emp].intersection(player_tiles))
                        idx_two=len(expDict[emp].intersection(opponent_tiles))
                        idx_three=len(expDict[emp].intersection(empty_posit)) #could be buggy this line
                        if idx_one<3 and idx_two<3:
                            liz.append((emp,Q[(idx_one,idx_two)][idx_three]))
                    try:
                        if win_flag==True:
                            for w in win_combis[wewe]:
                                if board[w]==0:
                                    pos=w
                        elif flag==True and win_flag==False:
                            for b in win_combis[block_index]:
                                if board[b]==0:
                                    pos=b
                        else:
                            pos=max(liz,key=itemgetter(1))[0]
                    except ValueError:
                        pos=random.choice(empty_positions)
                    board[pos]=player_num #make the guess move
                    turn=False #move made 
                    draw_square(pos,blue)
                    return
        

    if mode==True: #train mode 
        # code for alternate automatic train mode , motivation more practical and use
        # q learning eq Q[s]=R[s]+alpha*max(next state, all actions)
        gameDisplay.fill(white)
        iterations=int(inputbox.ask(gameDisplay,'Number of iterations'))
        GamesTrained+=iterations
        counter=0
        while not game_exit:
            if game_over==True:
                db['ku']=Q              
                db['gt']=GamesTrained
                gameDisplay.fill(white)
                message_to_screen('Done',blue,-70,'medium')
                message_to_screen('press R for replay',black,30,'small')
                pygame.display.update()
            while game_over:
                for event in pygame.event.get():
                    if event.type==pygame.KEYDOWN:
                        if event.key==pygame.K_r:
                            game_over=False
                            game_intro()
                    if event.type==pygame.QUIT:
                        game_exit=True
                        pygame.quit()
                        quit()
            for event in pygame.event.get():
                if event.type==pygame.QUIT:
                    game_exit=True
                    pygame.quit()
                    quit()
            #in the following loop the game is played varying the board directly
            # no display updates and it is between random player and boltzmann player
            #time_onY=0
            while counter < iterations :
                counter+=1
                gameDisplay.fill(white)
                message_to_screen('Episode %d'%(counter),blue,-70,'medium')
                #pygame.time.delay(1000)
                pygame.display.update()
                Reward=0
                plays_first=random.randint(1,2) #choose who plays first boltzmann or random 
                # boltz_moves=[] #list of moves played by boltz in a sequence to be used for updates 
                QIndexes=[] ## indexes in new Q structure which have to be updated
                #print 'Episode %d and plays_first %d' %(counter,plays_first)
                #start=time.clock()
                if plays_first==1: #boltzmann plays first
                    boltz_move=[]
                    boltz_move.append((random.choice([x for x in xrange(9)])))
                    board[boltz_move[-1]]=1 #first move random
                    QIndexes.append((0,0,len(expDict[boltz_move[-1]]))) ##buggy code??
                    while who_won(board)=='': #bust out of the loop when win lose or tie
                        dumb_player(2) #let random play since boltz already played
                        empty_squares=set([x for x,y in enumerate(board) if y==0]) ## [e for e,o in enumerate(board) if o==0]
                        player_squares=set([x for x,y in enumerate(board) if y==1])
                        opponent_squares=set([x for x,y in enumerate(board) if y==2])
                        boltz_move.append(dumb_player(1)) ##store sequence of moves made by us
                        if who_won(board)=='' and empty_squares!=[]:
                            index_one=len(expDict[boltz_move[-1]].intersection(player_squares))
                            index_two=len(expDict[boltz_move[-1]].intersection(opponent_squares))
                            index_three=len(expDict[boltz_move[-1]].intersection(empty_squares))
                            if index_one<3 and index_two<3:
                                QIndexes.append((index_one,index_two,index_three))
                    if who_won(board)=='P1 wins':
                        Reward=10
                    elif who_won(board)=='P2 wins':
                        Reward=-50
                    else:
                        Reward=-1
                
                elif plays_first==2: #random plays first
                    boltz_move=[]
                    dumb_player(1) #first move random
                    #print board
                    while who_won(board)=='': #bust out of the loop when win lose or tie
                        empty_squares=set([x for x,y in enumerate(board) if y==0]) ## [e for e,o in enumerate(board) if o==0]
                        player_squares=set([x for x,y in enumerate(board) if y==2])
                        opponent_squares=set([x for x,y in enumerate(board) if y==1])
                        boltz_move.append(dumb_player(2))
                    #    print 'after we play {0}'.format(board)
                        if who_won(board)=='' and empty_squares!=[]:
                            index_one=len(expDict[boltz_move[-1]].intersection(player_squares)) #does not necessarily mean
                            index_two=len(expDict[boltz_move[-1]].intersection(opponent_squares))
                            index_three=len(expDict[boltz_move[-1]].intersection(empty_squares))
                            if index_one<3 and index_two<3: ##avoid foolish situations somebody should have won by now
                                QIndexes.append((index_one,index_two,index_three))
                        dumb_player(1)
                    #    print 'after opp plays {0}'.format(board)
                    if who_won(board)=='P1 wins':
                        Reward=-50
                    elif who_won(board)=='P2 wins':
                        Reward=10
                    else:
                        Reward=-1
               # end=time.clock()
                #print 'QIndexes {0}'.format(QIndexes)
               # time_onY+=end-start
                for pl,ol,el in QIndexes:  ###accordingly update new Q structure 
                    Q[(pl,ol)][el]+= alpha*(Reward-Q[(pl,ol)][el])
                board=[0 for _ in xrange(9)] #refresh the board after each episode
               # with open('stateone.txt','a') as text_file:
                #    print('X1 : {} X2 : {} X3 : {}  X4 : {} X5 : {} X6 : {} X7 : {} X8 : {} X9 : {}  Y : {}'.format(Q[(0,0)][0],Q[(0,0)][1],Q[(0,0)][2],Q[(0,0)][3],Q[(0,0)][4],Q[(0,0)][5],Q[(0,0)][6],Q[(0,0)][7],Q[(0,0)][8],time_onY),file=text_file)
                #print Q
            game_over=True
            gameDisplay.fill(white)
            pygame.display.update()
            clock.tick(FPS)
        
    else:  #play mode
        while not game_exit:
            if who_won(board)!='':
                game_over=True
            if game_over==True:
                if who_won(board)=='tie':
                    GamesTied+=1
                    db['tt']=GamesTied
                if who_won(board)=='P1 wins' and plays_first==1:
                    GamesWon+=1
                    db['gw']=GamesWon
                if who_won(board)=='P2 wins' and plays_first==2:
                    GamesWon+=1
                    db['gw']=GamesWon
                plays_first=2 # 1 when cpu plays first else 2 
                if random.randint(1,2)==1:
                #    global turn   
                    turn=True
                    plays_first=1
                gameDisplay.fill(black)
                message_to_screen(who_won(board),green,0,'large') #update display for game over get q values  in train mode in play mode display winner  
                message_to_screen('press R for replay',white,70,'small')
                pygame.display.update() # message_to_screen(repr(board),green,100,'medium')
            while  game_over:
                for event in pygame.event.get():
                    if event.type==pygame.KEYDOWN:
                        if event.key==pygame.K_r:
                            game_over=False
                            game_intro()
                    if event.type==pygame.QUIT:
                        game_over=False
                        game_exit=True
                        pygame.quit()
                        quit()
            if plays_first==1:
                smart_player(plays_first)
          
            for event in pygame.event.get():
                if event.type==pygame.QUIT:
                    game_exit=True
                if event.type==pygame.MOUSEBUTTONDOWN:
                    if not turn: #our turn
                        spot=pygame.mouse.get_pos()
                        spot=pos_map[(spot[0]//200,spot[1]//200)] #get spot gonna be used twice so lookup once
                        if plays_first==1:
                            board[spot]=2
                            turn=True
                            draw_square(spot,red)
                            if game_over==False:
                                smart_player(plays_first)
                            if who_won(board)!='':
                                game_over=True
                        else:
                            board[spot]=1
                            turn=True
                            draw_square(spot,red)
                            if game_over==False:
                                smart_player(plays_first)
                            if who_won(board)!='':
                                game_over=True
            #drawing the board 
            gameDisplay.fill(white) # pygame.draw.line(surface_obj,color,(x1,y1),(x2,y2),width= try some vals)
            pygame.draw.line(gameDisplay,black,(200,0),(200,600),4)
            pygame.draw.line(gameDisplay,black,(400,0),(400,600),4)
            pygame.draw.line(gameDisplay,black,(0,200),(600,200),4)
            pygame.draw.line(gameDisplay,black,(0,400),(600,400),4)
            pygame.display.update(update_list)
            pygame.time.delay(1000)
            clock.tick(FPS)

    pygame.quit()
    quit()
game_intro()

