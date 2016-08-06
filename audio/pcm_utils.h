#ifndef PCM_UTILS_H
#define PCM_UTILS_H

#define ERR_PCM_MISC         -99
#define ERR_PCM_OPEN          -1
#define ERR_PCM_PARAM         -2
#define ERR_PCM_THREAD_CREATE -3
#define ERR_PCM_QUEUE         -4
#define ERR_FILE_NOT_FOUND    -5
#define ERR_PCM_MEMORY        -6

#ifndef MIN
#define MIN(x,y) ((x)>(y)?(y):(x))
#endif 

#ifndef MAX
#define MAX(x,y) ((x)>(y)?(x):(y))
#endif

#ifndef FALSE
#define FALSE 0
#endif

#ifndef TRUE
#define TRUE 1
#endif

#endif // PCM_UTILS_H