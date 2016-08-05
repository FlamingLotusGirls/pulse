// XXX - why dont I add to the head of the list, rather than the tail? Much easier. FIXME
#include <stdlib.h>
#include "linked_list.h"

LinkedList* LinkedListAdd(LinkedList *list, void *data)
{
    LinkedList *newList = (LinkedList *)malloc(sizeof(LinkedList));
    newList->data = data;
    newList->next = NULL;

    if (!list) {
        return newList;
    }
    
    LinkedList *tail;
    LinkedList *curElement = list;
    while (curElement) {
       tail = curElement; 
       curElement = curElement->next;
    }
    
    tail->next = newList;
    
    return list;
}

LinkedList* LinkedListDelete(LinkedList *list, void *data)
{
    LinkedList *prev = NULL;
    LinkedList *cur = list;
    LinkedList *ret = list;
    while (cur) {
        if (cur->data == data) {
            if (prev) {
                prev->next = cur->next;
            } else {
                ret = cur->next;
            }
            free(cur);
            break;
        }
        prev = cur;
        cur = cur->next;
    }
    
    return ret;
}