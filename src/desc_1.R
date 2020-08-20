# descriptive 1
wlog("Google Trends: Round 1 Descriptive",head=T,level=1)
wlog("==================================",level=1)
wlog("==================================",level=1)



wlog("The google trends currently selected:",KEYWORDS)


start<-Sys.time()
#Mom's selected SEO Keywords
# keywords<-c('amazon spa','mountain spa','mountain getaway','majestic resort','exclusive travel')
keywords<-KEYWORDS
# keywords<-c('spa','a','mountain getaway','majestic resort','exclusive travel')
# paste0(Sys.Date()-7,"T06 ",Sys.Date()-1,"T06")->tf

# lastweek_trends<-gtrends(keywords,time=tf)
historic_trends<-gtrends(keywords,time=paste("2004-04-01",Sys.Date()))
names(lastweek_trends)->nmz

historic_trends[['interest_over_time']]%>% dplyr::group_by(keyword,format(date,"%Y")
) %>% 
  dplyr::summarise(mean_hits = sum(as.numeric(hits),na.rm = T) / n())%>%
  tidyr::spread(`format(date, "%Y")`,mean_hits)%>%
  dplyr::select(c(1,(ncol(.)-3):(ncol(.))))%>%
  cbind.data.frame(.,data.frame(mean = apply(.[,-1],1,mean)))




historic_trends[['related_queries']]%>%dplyr::filter(subject%in%c('100'#,'Breakout'
))%>%#dplyr::select(subject,keyword,value)%>%
  dplyr::pull(value)->r1_words#%>%pull(value)
#This component enables you to contrast the competitiveness of the keywords selected with the 

r1week_trends2<-lapply(c("CA","US","NZ","AU","GB"),function(x)gtrends(r1_words,time=tf,geo = x))
r1hist_trends2<-lapply(c("CA","US","NZ","AU","GB"),function(x)gtrends(r1_words,time=paste("2004-04-01",Sys.Date()),geo = x))
r1week_trends<-gtrends(r1_words,time=tf)
r1hist_trends<-gtrends(r1_words,time=paste("2004-04-01",Sys.Date()))
# data(countries)
end<-Sys.time()
end-start

historic_trends[[1]]%>%
  dplyr::mutate(date=as.Date(date),
                hits = purrr::map_dbl(.x=hits,~{
                  .x <- if(typeof(.x) == 'character'){
                    as.numeric(gsub('<','',.x))
                  } else {
                    .x
                  }
                }))%>%
  tibbletime::tbl_time(index = 'date')%>%
  .[complete.cases(.$hits),] %>%
  ggplot(aes(date, hits, colour = keyword))+ 
  geom_area(aes(color = keyword, fill = keyword), 
            alpha = 0.5, position = position_dodge(0.8)) + 
  # geom_line(aes(colour = keyword), 
  #           alpha = 0.5)+
  labs(
    x = "Date (since 2005)",
    y = "Hits (Relative)",
    title = "Trends in Online Marketing",
    caption = "Source: Google Trends"
  )+
  ggthemes::theme_tufte()+
  theme(axis.title.y=element_blank(),
        axis.text.y=element_blank(),
        axis.ticks.y=element_blank()) +
  scale_color_manual(values = c("#00AFBB", "#E7B800","#6600ff","#000000","#CC3333")) +
  scale_fill_manual(values = c("#00AFBB", "#E7B800","#6600ff","#000000","#CC3333"))#+
  # facet_wrap(~ keyword, ncol = 1,scales = "free_y") 
